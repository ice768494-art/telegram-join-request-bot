import logging
import os
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
CHANNEL_ID = os.getenv("CHANNEL_ID", "").strip()
EXPIRE_MINUTES = int(os.getenv("LINK_EXPIRE_MINUTES", "30"))
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing.")
if not CHANNEL_ID:
    raise RuntimeError("CHANNEL_ID is missing.")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("request-join-bot")

stats = {
    "users": set(),
    "links_created": 0,
    "join_requests": 0,
}


def is_admin(user_id: int) -> bool:
    return bool(ADMIN_ID) and str(user_id) == ADMIN_ID


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    stats["users"].add(update.effective_user.id)

    try:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)

        invite = await context.bot.create_chat_invite_link(
            chat_id=CHANNEL_ID,
            name=f"User {update.effective_user.id}"[:32],
            expire_date=expires_at,
            creates_join_request=True,
        )

        button = InlineKeyboardButton(
            "• REQUEST TO JOIN •",
            url=invite.invite_link,
        )

        text = (
            "⚡ <b>HERE IS YOUR LINK!</b>\n\n"
            "CLICK THE BUTTON BELOW TO PROCEED."
        )

        await update.message.reply_text(
            text,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[button]]),
        )

        await update.message.reply_text(
            "⚠️ <b>IF THE LINK EXPIRES, TRY AGAIN</b>\n"
            "OR CLICK THE POST LINK TO GET A NEW ONE.",
            parse_mode="HTML",
        )

        stats["links_created"] += 1

    except TelegramError as exc:
        logger.exception("Telegram error while creating invite link")
        await update.message.reply_text(
            "❌ I couldn't create the request link.\n\n"
            "Please make sure I am an administrator of the destination "
            "channel and can manage invite links."
        )
        logger.error("Telegram error: %s", exc)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    stats["users"].add(update.effective_user.id)

    if ADMIN_ID and not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    await update.message.reply_text(
        "📊 <b>BOT STATS</b>\n\n"
        f"👤 Users seen: <b>{len(stats['users'])}</b>\n"
        f"🔗 Links created: <b>{stats['links_created']}</b>\n"
        f"📨 Join requests seen: <b>{stats['join_requests']}</b>\n"
        f"⏳ Link lifetime: <b>{EXPIRE_MINUTES} minutes</b>",
        parse_mode="HTML",
    )


async def check_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.message:
        return

    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Admin only.")
        return

    try:
        chat = await context.bot.get_chat(CHANNEL_ID)
        member = await context.bot.get_chat_member(chat.id, context.bot.id)

        await update.message.reply_text(
            "✅ <b>CHANNEL CHECK</b>\n\n"
            f"📢 Channel: <b>{chat.title or 'Unknown'}</b>\n"
            f"🆔 ID: <code>{chat.id}</code>\n"
            f"🤖 Bot status: <b>{member.status}</b>\n\n"
            "If /start still cannot create links, check that the bot "
            "has permission to manage invite links.",
            parse_mode="HTML",
        )
    except TelegramError as exc:
        await update.message.reply_text(
            "❌ Channel check failed.\n\n"
            "Verify CHANNEL_ID and make sure the bot is an administrator "
            "of the channel."
        )
        logger.error("Channel check error: %s", exc)


async def join_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    request = update.chat_join_request
    if request:
        stats["join_requests"] += 1
        logger.info(
            "Join request: user=%s chat=%s",
            request.from_user.id,
            request.chat.id,
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error", exc_info=context.error)


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("check", check_command))

    from telegram.ext import ChatJoinRequestHandler
    application.add_handler(ChatJoinRequestHandler(join_request))

    application.add_error_handler(error_handler)

    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
