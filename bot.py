import logging
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ChatJoinRequestHandler,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
DEFAULT_EXPIRE = int(os.getenv("LINK_EXPIRE_MINUTES", "30"))
DB_PATH = os.getenv("DB_PATH", "bot.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")
if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID is missing.")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

db = sqlite3.connect(DB_PATH, check_same_thread=False)
db.execute("""
CREATE TABLE IF NOT EXISTS stats (
    key TEXT PRIMARY KEY,
    value INTEGER NOT NULL DEFAULT 0
)
""")
db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_seen TEXT NOT NULL
)
""")
db.commit()


def inc(key: str, amount: int = 1):
    db.execute(
        "INSERT INTO stats(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=value+excluded.value",
        (key, amount),
    )
    db.commit()


def get_stat(key: str) -> int:
    row = db.execute("SELECT value FROM stats WHERE key=?", (key,)).fetchone()
    return row[0] if row else 0


def save_user(user_id: int):
    db.execute(
        "INSERT OR IGNORE INTO users(user_id, first_seen) VALUES(?,?)",
        (user_id, datetime.now(timezone.utc).isoformat()),
    )
    db.commit()


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_ID) and str(user_id) == ADMIN_ID


def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 GET NEW LINK", callback_data="newlink")],
        [
            InlineKeyboardButton("⏳ 15 MIN", callback_data="exp:15"),
            InlineKeyboardButton("⏳ 30 MIN", callback_data="exp:30"),
            InlineKeyboardButton("⏳ 1 HOUR", callback_data="exp:60"),
        ],
    ])


async def make_link(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int):
    user = update.effective_user
    if not user:
        return

    save_user(user.id)

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=minutes)
        invite = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"Req {user.id}"[:32],
            expire_date=expires_at,
            creates_join_request=True,
        )
        inc("links_created")

        text = (
            "⚡ <b>HERE IS YOUR LINK!</b>\n\n"
            "CLICK THE BUTTON BELOW TO PROCEED.\n\n"
            f"⏳ <b>Expires in:</b> {minutes} minutes"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("• REQUEST TO JOIN •", url=invite.invite_link)
        ]])

        if update.callback_query:
            await update.callback_query.edit_message_text(
                text, parse_mode="HTML", reply_markup=keyboard
            )
            await update.callback_query.message.reply_text(
                "⚠️ <b>IF THE LINK EXPIRES, TRY AGAIN</b>\n"
                "OR TAP THE BUTTON BELOW TO GET A NEW ONE.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 GET NEW LINK", callback_data="newlink")
                ]]),
            )
        else:
            await update.message.reply_text(
                text, parse_mode="HTML", reply_markup=keyboard
            )
            await update.message.reply_text(
                "⚠️ <b>IF THE LINK EXPIRES, TRY AGAIN</b>",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔄 GET NEW LINK", callback_data="newlink")
                ]]),
            )

    except Exception:
        logger.exception("Could not create invite link")
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text(
            "❌ I couldn't create the link.\n\n"
            "Make sure the bot is an administrator of the channel and "
            "has permission to manage invite links."
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    save_user(update.effective_user.id)
    await update.message.reply_text(
        "⚡ <b>WELCOME!</b>\n\n"
        "Generate a temporary request-to-join link below.",
        parse_mode="HTML",
        reply_markup=home_keyboard(),
    )


async def newlink(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await make_link(update, context, DEFAULT_EXPIRE)


async def expiry_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    minutes = int(query.data.split(":")[1])
    await make_link(update, context, minutes)


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not update.message:
        return
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 STATISTICS", callback_data="admin_stats")],
        [
            InlineKeyboardButton("⏳ DEFAULT 15M", callback_data="setdefault:15"),
            InlineKeyboardButton("⏳ DEFAULT 30M", callback_data="setdefault:30"),
        ],
        [InlineKeyboardButton("⏳ DEFAULT 1H", callback_data="setdefault:60")],
        [InlineKeyboardButton("🔍 CHECK CHANNEL", callback_data="admin_check")],
    ])
    await update.message.reply_text(
        "🔐 <b>ADMIN PANEL</b>\n\nChoose an action:",
        parse_mode="HTML",
        reply_markup=keyboard,
    )


async def admin_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global DEFAULT_EXPIRE
    query = update.callback_query
    await query.answer()

    if not query.from_user or not is_admin(query.from_user.id):
        await query.answer("Admin only.", show_alert=True)
        return

    if query.data == "admin_stats":
        users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        text = (
            "📊 <b>BOT STATISTICS</b>\n\n"
            f"👤 Users: <b>{users}</b>\n"
            f"🔗 Links created: <b>{get_stat('links_created')}</b>\n"
            f"📨 Join requests: <b>{get_stat('join_requests')}</b>\n"
            f"⏳ Default expiry: <b>{DEFAULT_EXPIRE} min</b>"
        )
        await query.edit_message_text(text, parse_mode="HTML")
        return

    if query.data.startswith("setdefault:"):
        DEFAULT_EXPIRE = int(query.data.split(":")[1])
        await query.edit_message_text(
            f"✅ Default link expiry is now <b>{DEFAULT_EXPIRE} minutes</b>.",
            parse_mode="HTML",
        )
        return

    if query.data == "admin_check":
        try:
            chat = await context.bot.get_chat(CHANNEL_ID)
            member = await context.bot.get_chat_member(chat.id, context.bot.id)
            await query.edit_message_text(
                "✅ <b>CHANNEL CHECK</b>\n\n"
                f"📢 {chat.title or 'Unknown'}\n"
                f"🆔 <code>{chat.id}</code>\n"
                f"🤖 Bot status: <b>{member.status}</b>",
                parse_mode="HTML",
            )
        except Exception:
            logger.exception("Channel check failed")
            await query.edit_message_text(
                "❌ Channel check failed.\nCheck CHANNEL_ID and bot permissions."
            )


async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    if request:
        inc("join_requests")
        logger.info("Join request from %s", request.from_user.id)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error: %s", context.error)


def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CallbackQueryHandler(newlink, pattern=r"^newlink$"))
    application.add_handler(CallbackQueryHandler(expiry_button, pattern=r"^exp:(15|30|60)$"))
    application.add_handler(CallbackQueryHandler(admin_button, pattern=r"^admin_.*$|^setdefault:\d+$"))
    application.add_handler(ChatJoinRequestHandler(join_request))
    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
