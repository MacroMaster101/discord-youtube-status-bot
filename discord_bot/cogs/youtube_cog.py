"""YouTube commands group: yt stats, link."""
import discord
from discord.ext import commands
from core import state
from youtube import api as yt_api
from config import Config


class YouTubeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(name="yt", invoke_without_command=True)
    async def yt(self, ctx: commands.Context):
        p = Config.PREFIX
        embed = discord.Embed(title="📺 YouTube Commands", color=0xFF0000)
        embed.add_field(name="Commands", value=(
            f"`{p}yt stats [channel]` — Show subscriber & view counts for a channel\n"
            f"`{p}yt link` — Get the direct link of the primary YouTube channel"
        ))
        await ctx.send(embed=embed)

    @yt.command(name="stats")
    async def stats(self, ctx: commands.Context, *, channel: str = None):
        target_channel = (channel or "").strip()
        if not target_channel:
            target_channel = Config.YOUTUBE_CHANNEL_ID
            
        if not target_channel:
            return await ctx.send("❌ No primary YouTube channel ID configured. Please specify a channel or configure it in the dashboard.")

        try:
            info = await yt_api.resolve_channel(target_channel)
        except yt_api.YouTubeError as e:
            return await ctx.send(f"❌ YouTube error: {e}")
            
        if not info:
            return await ctx.send("❌ Could not find that channel.")
            
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
        await ctx.send(embed=embed)

    @yt.command(name="link")
    async def link(self, ctx: commands.Context):
        if not Config.YOUTUBE_CHANNEL_ID:
            return await ctx.send("❌ No primary YouTube channel configured. Set it in the dashboard.")
        url = f"https://www.youtube.com/channel/{Config.YOUTUBE_CHANNEL_ID}"
        await ctx.send(f"📺 **Direct Link to YouTube Channel:** <{url}>")
