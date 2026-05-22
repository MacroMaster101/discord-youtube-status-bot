"""Discord bot factory. Builds the commands.Bot with intents and registers everything."""
import discord
from discord.ext import commands
from config import Config
from core import state
from youtube.poller import setup_poller
from discord_bot import events
from discord_bot.presence import start_presence
from discord_bot.cogs.info import Info
from discord_bot.cogs.youtube_cog import YouTubeCog


def build_bot() -> commands.Bot:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.presences = True

    def get_prefix(bot_instance, message):
        return Config.PREFIX

    bot = commands.Bot(command_prefix=get_prefix, intents=intents, help_command=None)

    @bot.event
    async def on_ready():
        state.set_start_time()
        state.add_log(f"Logged in as {bot.user} (ID: {bot.user.id})", "success")
        state.add_log(f"Serving {len(bot.guilds)} server(s)", "info")
        # Prefix commands do not need slash tree syncing
        state.add_log("Prefix commands active", "success")
        # Eagerly fetch default channel stats on startup if configured
        if Config.YOUTUBE_CHANNEL_ID and Config.YOUTUBE_API_KEY:
            async def resolve_default():
                from youtube import api as yt_api
                try:
                    # Auto-resolve handle or URL to raw channel ID
                    channel_id = Config.YOUTUBE_CHANNEL_ID.strip()
                    if not (channel_id.startswith("UC") and len(channel_id) == 24):
                        state.add_log(f"Auto-resolving handle/URL '{channel_id}' to raw channel ID...", "info")
                        resolved = await yt_api.resolve_channel(channel_id)
                        if resolved and resolved.get("id"):
                            channel_id = resolved["id"]
                            Config.update_env("YOUTUBE_CHANNEL_ID", channel_id)
                            state.add_log(f"Successfully normalized channel ID: {channel_id}", "success")
                        else:
                            state.add_log(f"Could not resolve channel ID for: {channel_id}", "error")
                            return

                    info = await yt_api.resolve_channel(channel_id)
                    if info:
                        live, upcoming, latest = None, None, None
                        try:
                            live = await yt_api.live_stream(channel_id)
                        except Exception:
                            pass
                        try:
                            upcoming = await yt_api.upcoming_stream(channel_id)
                        except Exception:
                            pass
                        try:
                            latest = await yt_api.latest_video(channel_id)
                        except Exception:
                            pass
                        state.YT_CHANNEL_CACHE[channel_id] = {
                            "title": info["title"],
                            "description": info.get("description", ""),
                            "thumbnail": info.get("thumbnail"),
                            "subscriber_count": info["subscriber_count"],
                            "view_count": info.get("view_count", 0),
                            "video_count": info.get("video_count", 0),
                            "hidden_subs": info.get("hidden_subs", False),
                            "url": f"https://www.youtube.com/channel/{channel_id}",
                            "live_url": live["url"] if live else None,
                            "live_title": live["title"] if live else None,
                            "upcoming_title": upcoming["title"] if upcoming else None,
                            "upcoming_url": upcoming["url"] if upcoming else None,
                            "latest_video_title": latest["title"] if latest else None,
                            "latest_video_url": latest["url"] if latest else None,
                        }
                        state.add_log(f"Successfully cached main channel: {info['title']}", "success")
                        
                        # Instantly update presence to reflect the cached channel stats
                        try:
                            from discord_bot.presence import _pick, _STATUS_MAP
                            activity, preview = _pick(bot)
                            status = _STATUS_MAP.get(state.CUSTOM_PRESENCE_STATUS, discord.Status.online)
                            await bot.change_presence(status=status, activity=activity)
                            state.CURRENT_PRESENCE = preview
                            state.add_log("Bot presence initialized successfully", "info")
                        except Exception as pe:
                            state.add_log(f"Immediate presence setup failed: {pe}", "warning")
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
    await bot.add_cog(YouTubeCog(bot))
