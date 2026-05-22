"""Info slash commands: stats, userinfo, avatar, servericon, ping, uptime, help."""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from core import state, storage


class Info(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Show bot latency")
    async def ping(self, inter: discord.Interaction):
        latency = round(self.bot.latency * 1000)
        embed = discord.Embed(title="🏓 Pong!", color=0x5865F2)
        embed.add_field(name="Latency", value=f"`{latency}ms`")
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="uptime", description="How long the bot has been online")
    async def uptime(self, inter: discord.Interaction):
        secs = state.uptime_seconds()
        h, r = divmod(secs, 3600)
        m, s = divmod(r, 60)
        d, h = divmod(h, 24)
        embed = discord.Embed(title="⏱️ Bot Uptime", color=0x57F287,
                              description=f"**{d}d {h}h {m}m {s}s**")
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="stats", description="Show server statistics")
    async def stats(self, inter: discord.Interaction):
        guild = inter.guild
        total_members = guild.member_count
        online = sum(1 for m in guild.members if m.status != discord.Status.offline and not m.bot)
        bots = sum(1 for m in guild.members if m.bot)
        yt_count = len(storage.yt_list_for_guild(guild.id))

        embed = discord.Embed(title=f"📊 {guild.name} — Server Stats",
                              color=0x5865F2, timestamp=datetime.datetime.utcnow())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="👥 Members", value=f"{total_members:,}", inline=True)
        embed.add_field(name="🟢 Online", value=f"{online:,}", inline=True)
        embed.add_field(name="🤖 Bots", value=f"{bots:,}", inline=True)
        embed.add_field(name="💬 Text", value=str(len(guild.text_channels)), inline=True)
        embed.add_field(name="🔊 Voice", value=str(len(guild.voice_channels)), inline=True)
        embed.add_field(name="📂 Categories", value=str(len(guild.categories)), inline=True)
        embed.add_field(name="📺 YouTube tracked", value=str(yt_count), inline=True)
        embed.add_field(name="👑 Owner", value=str(guild.owner), inline=True)
        embed.add_field(name="📅 Created", value=guild.created_at.strftime("%b %d, %Y"), inline=True)
        embed.set_footer(text=f"Requested by {inter.user}", icon_url=inter.user.display_avatar.url)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a user")
    async def userinfo(self, inter: discord.Interaction, member: discord.Member = None):
        member = member or inter.user
        roles = [r.mention for r in member.roles if r.name != "@everyone"]
        embed = discord.Embed(title=f"👤 {member}", color=member.color or 0x5865F2,
                              timestamp=datetime.datetime.utcnow())
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="ID", value=f"`{member.id}`", inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        embed.add_field(name="Status", value=str(member.status).title(), inline=True)
        embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"), inline=True)
        embed.add_field(name="Joined", value=member.joined_at.strftime("%b %d, %Y") if member.joined_at else "N/A",
                        inline=True)
        embed.add_field(name="Top Role",
                        value=member.top_role.mention if member.top_role.name != "@everyone" else "None",
                        inline=True)
        embed.add_field(name=f"Roles ({len(roles)})",
                        value=", ".join(roles[:10]) or "None", inline=False)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="avatar", description="Show a user's avatar")
    async def avatar(self, inter: discord.Interaction, member: discord.Member = None):
        user = member or inter.user
        embed = discord.Embed(title=f"🖼️ {user.name}'s Avatar", color=0x5865F2)
        embed.set_image(url=user.display_avatar.with_size(1024).url)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="servericon", description="Show the server's icon")
    async def servericon(self, inter: discord.Interaction):
        guild = inter.guild
        if not guild.icon:
            return await inter.response.send_message("This server has no icon.", ephemeral=True)
        embed = discord.Embed(title=f"🖼️ {guild.name}", color=0x5865F2)
        embed.set_image(url=guild.icon.with_size(1024).url)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="help", description="List all bot commands")
    async def help(self, inter: discord.Interaction):
        embed = discord.Embed(title="📖 Bot Commands", color=0xFF0000,
                              timestamp=datetime.datetime.utcnow())
        embed.add_field(name="📺 YouTube", value=(
            "`/yt subscribe` — Get pinged when a channel uploads\n"
            "`/yt unsubscribe` — Remove a subscription\n"
            "`/yt list` — Show this server's tracked channels\n"
            "`/yt stats` — Show subscriber/view counts for any channel"
        ), inline=False)
        embed.add_field(name="📊 Info", value=(
            "`/stats` `/userinfo` `/avatar` `/servericon` `/ping` `/uptime`"
        ), inline=False)
        embed.add_field(name="🎮 Fun", value=(
            "`/roll` `/flip` `/8ball` `/rps` `/poll`"
        ), inline=False)
        await inter.response.send_message(embed=embed)
