"""YouTube slash command group: /yt subscribe, unsubscribe, list, stats."""
import discord
from discord import app_commands
from discord.ext import commands
from core import state, storage
from youtube import api as yt_api


class YouTubeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    yt = app_commands.Group(name="yt", description="YouTube channel tracking & stats")

    @yt.command(name="subscribe", description="Get notified when a YouTube channel uploads")
    @app_commands.describe(
        channel="YouTube channel URL, @handle, or channel ID",
        post_to="Discord channel to post notifications in (defaults to current channel)",
    )
    @app_commands.default_permissions(manage_channels=True)
    async def subscribe(self, inter: discord.Interaction, channel: str,
                        post_to: discord.TextChannel = None):
        await inter.response.defer()
        target = post_to or inter.channel
        try:
            info = await yt_api.resolve_channel(channel)
        except yt_api.YouTubeError as e:
            return await inter.followup.send(f"❌ YouTube error: {e}", ephemeral=True)
        if not info:
            return await inter.followup.send("❌ Could not find that channel.", ephemeral=True)
        added = storage.yt_add(inter.guild.id, target.id, info["id"], info["title"])
        if not added:
            return await inter.followup.send(
                f"ℹ️ Already subscribed to **{info['title']}** in {target.mention}.", ephemeral=True)
        embed = discord.Embed(
            title=f"📺 Now tracking {info['title']}",
            description=f"New uploads will be posted in {target.mention}.",
            color=0xFF0000,
        )
        if info.get("thumbnail"):
            embed.set_thumbnail(url=info["thumbnail"])
        if not info.get("hidden_subs"):
            embed.add_field(name="Subscribers", value=f"{info['subscriber_count']:,}", inline=True)
        embed.add_field(name="Videos", value=f"{info['video_count']:,}", inline=True)
        await inter.followup.send(embed=embed)
        state.add_log(f"YT subscribe: {info['title']} → #{target.name} in {inter.guild.name}", "success")

    @yt.command(name="unsubscribe", description="Stop tracking a YouTube channel")
    @app_commands.describe(channel="YouTube channel URL, @handle, or channel ID",
                           post_to="Discord channel where it was subscribed (defaults to current)")
    @app_commands.default_permissions(manage_channels=True)
    async def unsubscribe(self, inter: discord.Interaction, channel: str,
                          post_to: discord.TextChannel = None):
        await inter.response.defer()
        target = post_to or inter.channel
        try:
            info = await yt_api.resolve_channel(channel)
        except yt_api.YouTubeError as e:
            return await inter.followup.send(f"❌ YouTube error: {e}", ephemeral=True)
        if not info:
            return await inter.followup.send("❌ Could not find that channel.", ephemeral=True)
        removed = storage.yt_remove(inter.guild.id, target.id, info["id"])
        if removed:
            await inter.followup.send(f"✅ Unsubscribed from **{info['title']}** in {target.mention}.")
            state.add_log(f"YT unsubscribe: {info['title']} from #{target.name}", "info")
        else:
            await inter.followup.send(f"ℹ️ No subscription for **{info['title']}** in {target.mention}.", ephemeral=True)

    @yt.command(name="list", description="Show YouTube channels tracked in this server")
    async def list_subs(self, inter: discord.Interaction):
        subs = storage.yt_list_for_guild(inter.guild.id)
        if not subs:
            return await inter.response.send_message("📭 No YouTube channels tracked yet. Use `/yt subscribe`.",
                                                     ephemeral=True)
        embed = discord.Embed(title=f"📺 Tracked YouTube channels — {inter.guild.name}",
                              color=0xFF0000)
        for s in subs[:25]:
            ch = inter.guild.get_channel(int(s["discord_channel_id"]))
            embed.add_field(
                name=s["yt_channel_title"],
                value=f"→ {ch.mention if ch else '`(channel missing)`'}\n`{s['yt_channel_id']}`",
                inline=False,
            )
        embed.set_footer(text=f"{len(subs)} total")
        await inter.response.send_message(embed=embed)

    @yt.command(name="stats", description="Show subscriber & view counts for a YouTube channel")
    async def stats(self, inter: discord.Interaction, channel: str):
        await inter.response.defer()
        try:
            info = await yt_api.resolve_channel(channel)
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
