"""Entry point. Loads config, builds the bot, starts the Flask dashboard, runs the bot."""
import asyncio
from config import Config
from core import state
from discord_bot.client import build_bot, setup_cogs
from web.app import keep_alive


def main():
    if not Config.DISCORD_TOKEN:
        print("ERROR: DISCORD_TOKEN not set in .env")
        return

    bot = build_bot()

    async def setup_hook():
        await setup_cogs(bot)
    bot.setup_hook = setup_hook

    keep_alive(bot)
    state.add_log("Starting bot...", "info")
    bot.run(Config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
