# Telegram Request-to-Join Bot V2

## Railway variables

BOT_TOKEN = BotFather token
CHANNEL_ID = @PublicChannelUsername or -100... for a private channel
LINK_EXPIRE_MINUTES = 30
ADMIN_ID = your numeric Telegram user ID
DB_PATH = bot.db

## Commands

/start - user menu
/admin - admin panel (ADMIN_ID only)

## Features

- Screenshot-style request-to-join flow
- Temporary links
- 15 / 30 / 60 minute expiry buttons
- Admin statistics
- Admin channel check
- SQLite statistics
- No secrets in source code

## Deploy

Connect this repo to Railway and use:

python bot.py

Do not commit .env or your real bot token.
