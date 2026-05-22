"""YouTube slash command group: /yt stats, link."""
import discord
from discord import app_commands
from discord.ext import commands
from core import state
from youtube import api as yt_api
from config import Config


class YouTubeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    yt = app_commands.Group(name="yt", description="YouTube channel tracking & stats")

    @yt.command(name="stats", description="Show subscriber & view counts for a YouTube channel")
    @app_commands.describe(channel="YouTube channel URL, @handle, or channel ID (optional, defaults to primary channel)")
    async def stats(self, inter: discord.Interaction, channel: str = None):
        await inter.response.defer()
        
        target_channel = (channel or "").strip()
        if not target_channel:
            target_channel = Config.YOUTUBE_CHANNEL_ID
            
        if not target_channel:
            return await inter.followup.send("❌ No primary YouTube channel ID configured. Please specify a channel or configure it in the dashboard.", ephemeral=True)

        try:
            info = await yt_api.resolve_channel(target_channel)
        except yt_api.YouTubeError as e:
            return await inter.followup.send(f"❌ YouTube error: {e}", ephemeral=True)
            
        if not info:
            return await inter.followup.send("❌ Could not find that channel.", ephemeral=True)
            
        try:
            latest = await yt_api.latest_video(info["id"])
        except yt_api.YouTubeError:
            latest = None

        embed = discord.Embed(
            title=f"📺 {info['title']}",
            url=f"https://www.youtube.com/channel/{info['id']}",
            description=info.get("description", "")[:300] or None,
            color=0xFF0000,
        )
        if info.get("thumbnail"):
            embed.set_thumbnail(url=info["thumbnail"])
        if not info.get("hidden_subs"):
            embed.add_field(name="👥 Subscribers", value=f"{info['subscriber_count']:,}", inline=True)
        embed.add_field(name="👁️ Total Views", value=f"{info['view_count']:,}", inline=True)
        embed.add_field(name="🎬 Videos", value=f"{info['video_count']:,}", inline=True)
        if latest:
            embed.add_field(
                name="🆕 Latest Video",
                value=f"[{latest['title']}]({latest['url']})",
                inline=False,
            )
        await inter.followup.send(embed=embed)

    @yt.command(name="link", description="Get the direct link of the primary YouTube channel")
    async def link(self, inter: discord.Interaction):
        if not Config.YOUTUBE_CHANNEL_ID:
            return await inter.response.send_message("❌ No primary YouTube channel configured. Set it in the dashboard.", ephemeral=True)
        url = f"https://www.youtube.com/channel/{Config.YOUTUBE_CHANNEL_ID}"
        await inter.response.send_message(f"📺 **Direct Link to YouTube Channel:** <{url}>")
