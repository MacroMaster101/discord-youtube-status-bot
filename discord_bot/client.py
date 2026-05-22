"""Discord bot factory. Builds the commands.Bot with intents and registers everything."""
import discord
from discord.ext import commands
from config import Config
from core import state
from youtube.poller import setup_poller
from discord_bot import events
from discord_bot.presence import start_presence
from discord_bot.cogs.info import Info
from discord_bot.cogs.fun import Fun
from discord_bot.cogs.youtube_cog import YouTubeCog


def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True

    bot = commands.Bot(command_prefix=Config.PREFIX, intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        state.set_start_time()
        state.add_log(f"Logged in as {bot.user} (ID: {bot.user.id})", "success")
        state.add_log(f"Serving {len(bot.guilds)} server(s)", "info")
        try:
            synced = await bot.tree.sync()
            state.add_log(f"Synced {len(synced)} slash commands", "success")
        except Exception as e:
            state.add_log(f"Slash sync failed: {e}", "error")
        start_presence(bot)
        poller = setup_poller(bot)
        if not poller.is_running():
            poller.start()

    events.register(bot)
    return bot


async def setup_cogs(bot: commands.Bot):
    await bot.add_cog(Info(bot))
    await bot.add_cog(Fun(bot))
    await bot.add_cog(YouTubeCog(bot))
