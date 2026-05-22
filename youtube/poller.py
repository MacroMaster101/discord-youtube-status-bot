"""Background poller: refreshes channel cache (subs + live), checks for new uploads,
and posts them to Discord."""
import discord
from discord.ext import tasks
from config import Config
from core import state
from youtube import api as yt_api


def setup_poller(client: discord.Client):
    @tasks.loop(seconds=Config.YOUTUBE_POLL_INTERVAL)
    async def poll_youtube():
        if not Config.YOUTUBE_API_KEY or not Config.YOUTUBE_CHANNEL_ID:
            return

        # 1. Refresh metadata for the rotating presence
        info, live, upcoming, latest = None, None, None, None
        try:
            info = await yt_api.resolve_channel(Config.YOUTUBE_CHANNEL_ID)
        except Exception as e:
            state.add_log(f"YT cache resolve channel failed: {e}", "error")
            return

        if not info:
            return

        try:
            live = await yt_api.live_stream(Config.YOUTUBE_CHANNEL_ID)
        except Exception as e:
            state.add_log(f"YT cache check live failed: {e}", "warning")

        try:
            upcoming = await yt_api.upcoming_stream(Config.YOUTUBE_CHANNEL_ID)
        except Exception as e:
            state.add_log(f"YT cache check upcoming failed: {e}", "warning")

        try:
            latest = await yt_api.latest_video(Config.YOUTUBE_CHANNEL_ID)
        except Exception as e:
            state.add_log(f"YT cache check latest failed: {e}", "warning")

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

        if latest:
            if not Config.YOUTUBE_LAST_VIDEO_ID:
                Config.update_env("YOUTUBE_LAST_VIDEO_ID", latest["id"])
            elif Config.YOUTUBE_LAST_VIDEO_ID != latest["id"]:
                channel_id = Config.YOUTUBE_NOTIFY_CHANNEL_ID or Config.WELCOME_CHANNEL_ID
                if channel_id:
                    posted = False
                    for guild in client.guilds:
                        channel = guild.get_channel(int(channel_id))
                        if channel:
                            embed = discord.Embed(
                                title=latest["title"],
                                url=latest["url"],
                                description=f"📺 New upload from **{info['title'] if info else latest.get('channel_title')}**",
                                color=0xFF0000,
                            )
                            if latest.get("thumbnail"):
                                embed.set_image(url=latest["thumbnail"])
                            embed.set_footer(text="YouTube", icon_url="https://www.youtube.com/s/desktop/12d6b690/img/favicon_144x144.png")
                            try:
                                await channel.send(content=f"🔔 **{info['title'] if info else latest.get('channel_title')}** just uploaded a new video!", embed=embed)
                                posted = True
                            except discord.Forbidden:
                                state.add_log(f"YT post forbidden in #{channel.name} ({guild.name})", "error")
                            except Exception as e:
                                state.add_log(f"YT post failed: {e}", "error")
                    if posted:
                        Config.update_env("YOUTUBE_LAST_VIDEO_ID", latest["id"])
                        state.add_yt_event(info["title"] if info else latest.get('channel_title'), latest["title"], latest["url"], "Discord")

    @poll_youtube.before_loop
    async def before():
        await client.wait_until_ready()

    return poll_youtube
