"""Entry point. Loads config, builds the bot, starts the Flask dashboard, runs the bot."""
import asyncio
from config import Config
from core import state
from discord_bot.client import build_bot, setup_cogs
from web.app import keep_alive


def main():
    bot = build_bot()

    async def setup_hook():
        await setup_cogs(bot)
    bot.setup_hook = setup_hook

    keep_alive(bot)

    token = Config.DISCORD_TOKEN
    if not token or token == "your_discord_bot_token_here":
        state.add_log("CRITICAL: DISCORD_TOKEN is missing or set to the default placeholder in .env!", "error")
        print("\n==========================================================")
        print("ERROR: DISCORD_TOKEN is not configured yet.")
        print("Please open your .env file and paste your Discord bot token.")
        print("The Flask web dashboard is still running on http://localhost:8080")
        print("==========================================================\n")
        
        # Keep Flask alive
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return

    state.add_log("Starting bot...", "info")
    try:
        bot.run(token, log_handler=None)
    except Exception as e:
        state.add_log(f"CRITICAL: Failed to launch bot: {e}", "error")
        print(f"\nCRITICAL: Bot login failed: {e}")
        print("The Flask web dashboard is still running on http://localhost:8080\n")
        
        # Keep Flask alive so the user can still check logs
        import time
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return


if __name__ == "__main__":
    main()
