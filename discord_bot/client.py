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
        # Eagerly fetch default channel stats on startup if configured
        if Config.YOUTUBE_CHANNEL_ID and Config.YOUTUBE_API_KEY:
            async def resolve_default():
                from youtube import api as yt_api
                try:
                    info = await yt_api.resolve_channel(Config.YOUTUBE_CHANNEL_ID)
                    if info:
                        live, upcoming, latest = None, None, None
                        try:
                            live = await yt_api.live_stream(Config.YOUTUBE_CHANNEL_ID)
                        except Exception:
                            pass
                        try:
                            upcoming = await yt_api.upcoming_stream(Config.YOUTUBE_CHANNEL_ID)
                        except Exception:
                            pass
                        try:
                            latest = await yt_api.latest_video(Config.YOUTUBE_CHANNEL_ID)
                        except Exception:
                            pass
                        state.YT_CHANNEL_CACHE[Config.YOUTUBE_CHANNEL_ID] = {
                            "title": info["title"],
                            "subscriber_count": info["subscriber_count"],
                            "view_count": info.get("view_count", 0),
                            "video_count": info.get("video_count", 0),
                            "hidden_subs": info.get("hidden_subs", False),
                            "url": f"https://www.youtube.com/channel/{Config.YOUTUBE_CHANNEL_ID}",
                            "live_url": live["url"] if live else None,
                            "live_title": live["title"] if live else None,
                            "upcoming_title": upcoming["title"] if upcoming else None,
                            "upcoming_url": upcoming["url"] if upcoming else None,
                            "latest_video_title": latest["title"] if latest else None,
                            "latest_video_url": latest["url"] if latest else None,
                        }
                        state.add_log(f"Successfully cached main channel: {info['title']}", "success")
                except Exception as e:
                    state.add_log(f"Failed eager resolution of main channel: {e}", "error")
            bot.loop.create_task(resolve_default())

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
