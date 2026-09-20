# Telegram Request-to-Join Link Bot

A simple Telegram bot that creates temporary invite links requiring a join request.

## Features

- `/start` creates a fresh Request-to-Join invite link.
- Links expire after `LINK_EXPIRE_MINUTES`.
- `/stats` shows basic in-memory statistics.
- `/check` lets the configured admin test the channel configuration.
- Join requests are logged by the bot.
- No bot token is stored in the source code.

## 1. Create the bot

Open Telegram and talk to `@BotFather`.

Use:

`/newbot`

Copy the token it gives you.

## 2. Add the bot to your channel

Open your destination channel:

Channel -> Edit -> Administrators -> Add Administrator

Give the bot permission to manage invite links / invite users via link.

For join-request updates, the bot also needs to be an administrator.

## 3. Set environment variables

Create these variables in Railway:

`BOT_TOKEN`
Your BotFather token.

`CHANNEL_ID`
For a public channel, for example:

`@MyChannel`

For a private channel, use the numeric channel ID, normally beginning with `-100`.

`LINK_EXPIRE_MINUTES`
For example:

`30`

`ADMIN_ID`
Your own numeric Telegram user ID. This is optional. If set, `/stats` and `/check` are restricted to that user.

Do not put your real `.env` file in GitHub.

## 4. Railway

Deploy the GitHub repository to Railway.

Railway should detect Python automatically. If it asks for a start command, use:

`python bot.py`

The included Procfile also provides:

`worker: python bot.py`

## 5. Test

After deployment, open your bot in Telegram and send:

`/start`

You should receive:

`⚡ HERE IS YOUR LINK!`

with:

`• REQUEST TO JOIN •`

Tap the button and send the join request.

If you configured `ADMIN_ID`, send:

`/check`

and:

`/stats`

## Important

The bot must generate its own invite links. It cannot manage invite links created by another administrator.

If Telegram returns a permission error, re-check that the bot is an administrator of the destination channel and can manage invite links.

## Security

Never publish `BOT_TOKEN` in GitHub, screenshots, public chats, or your website.

If your token is exposed, use BotFather to revoke/regenerate it.
