"""Background poller: refreshes channel cache (subs + live), checks for new uploads,
and posts them to Discord."""
import discord
from discord.ext import tasks
from config import Config
from core import state, storage
from youtube import api as yt_api


def setup_poller(client: discord.Client):
    @tasks.loop(seconds=Config.YOUTUBE_POLL_INTERVAL)
    async def poll_youtube():
        if not Config.YOUTUBE_API_KEY:
            return
        all_subs = storage.yt_list_all()

        # Build unique channel set, then refresh cache + check uploads.
        unique_channels = {}
        for guild_id, subs in all_subs.items():
            for sub in subs:
                unique_channels.setdefault(sub["yt_channel_id"], sub["yt_channel_title"])

        # Refresh metadata for the rotating presence (subs + live state).
        for yt_id, title in unique_channels.items():
            try:
                info = await yt_api.resolve_channel(yt_id)
                live = await yt_api.live_stream(yt_id)
            except yt_api.YouTubeError as e:
                state.add_log(f"YT cache refresh failed for {title}: {e}", "error")
                continue
            if not info:
                continue
            state.YT_CHANNEL_CACHE[yt_id] = {
                "title": info["title"],
                "subscriber_count": info["subscriber_count"],
                "view_count": info.get("view_count", 0),
                "video_count": info.get("video_count", 0),
                "hidden_subs": info.get("hidden_subs", False),
                "url": f"https://www.youtube.com/channel/{yt_id}",
                "live_url": live["url"] if live else None,
                "live_title": live["title"] if live else None,
            }

        # Check for new uploads + post notifications.
        for guild_id, subs in all_subs.items():
            guild = client.get_guild(int(guild_id))
            if guild is None:
                continue
            for sub in subs:
                try:
                    latest = await yt_api.latest_video(sub["yt_channel_id"])
                except yt_api.YouTubeError as e:
                    state.add_log(f"YT poll error for {sub['yt_channel_title']}: {e}", "error")
                    continue
                if not latest or sub["last_video_id"] == latest["id"]:
                    continue
                # First-time seeding: don't spam old videos on initial subscribe.
                if sub["last_video_id"] is None:
                    storage.yt_update_last_video(guild_id, sub["discord_channel_id"], sub["yt_channel_id"], latest["id"])
                    continue

                channel = guild.get_channel(int(sub["discord_channel_id"]))
                if channel is None:
                    continue
                embed = discord.Embed(
                    title=latest["title"],
                    url=latest["url"],
                    description=f"📺 New upload from **{sub['yt_channel_title']}**",
                    color=0xFF0000,
                )
                if latest.get("thumbnail"):
                    embed.set_image(url=latest["thumbnail"])
                embed.set_footer(text="YouTube",
                                 icon_url="https://www.youtube.com/s/desktop/12d6b690/img/favicon_144x144.png")
                try:
                    await channel.send(content=f"🔔 {sub['yt_channel_title']} just uploaded!", embed=embed)
                    storage.yt_update_last_video(guild_id, sub["discord_channel_id"], sub["yt_channel_id"], latest["id"])
                    state.add_yt_event(sub["yt_channel_title"], latest["title"], latest["url"], guild.name)
                except discord.Forbidden:
                    state.add_log(f"YT post forbidden in #{channel.name} ({guild.name})", "error")
                except Exception as e:
                    state.add_log(f"YT post failed: {e}", "error")

    @poll_youtube.before_loop
    async def before():
        await client.wait_until_ready()

    return poll_youtube
