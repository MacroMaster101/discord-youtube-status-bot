"""Moderation slash commands: kick, ban, unban, timeout, warn, purge, slowmode, lock, nick, roles."""
import datetime
import discord
from discord import app_commands
from discord.ext import commands
from config import Config
from core import state, storage


async def _send_mod_log(guild, title, description, color=0xED4245):
    if not Config.MOD_LOG_CHANNEL_ID:
        return
    try:
        ch = guild.get_channel(int(Config.MOD_LOG_CHANNEL_ID))
        if ch:
            embed = discord.Embed(title=title, description=description, color=color,
                                  timestamp=datetime.datetime.utcnow())
            await ch.send(embed=embed)
    except Exception as e:
        state.add_log(f"mod-log send failed: {e}", "error")


class Moderation(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from the server")
    @app_commands.describe(member="Member to kick", reason="Reason")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, inter: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if member.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return await inter.response.send_message("🚫 Can't kick equal/higher role.", ephemeral=True)
        try:
            await member.kick(reason=f"[{inter.user}] {reason}")
            await inter.response.send_message(f"👢 {member} has been kicked. Reason: {reason}")
            state.add_mod_action("kick", inter.user, member, reason, inter.guild.name)
            await _send_mod_log(inter.guild, "👢 Member Kicked",
                                f"**Member:** {member.mention}\n**Moderator:** {inter.user.mention}\n**Reason:** {reason}")
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.describe(member="Member to ban", reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, inter: discord.Interaction, member: discord.Member, reason: str = "No reason"):
        if member.top_role >= inter.user.top_role and inter.user != inter.guild.owner:
            return await inter.response.send_message("🚫 Can't ban equal/higher role.", ephemeral=True)
        try:
            await member.ban(reason=f"[{inter.user}] {reason}", delete_message_seconds=0)
            await inter.response.send_message(f"🔨 {member} has been banned. Reason: {reason}")
            state.add_mod_action("ban", inter.user, member, reason, inter.guild.name)
            await _send_mod_log(inter.guild, "🔨 Member Banned",
                                f"**Member:** {member.mention}\n**Moderator:** {inter.user.mention}\n**Reason:** {reason}")
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="unban", description="Unban a user by ID")
    @app_commands.describe(user_id="User ID to unban", reason="Reason")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, inter: discord.Interaction, user_id: str, reason: str = "No reason"):
        if not user_id.isdigit():
            return await inter.response.send_message("🚫 user_id must be numeric.", ephemeral=True)
        try:
            await inter.guild.unban(discord.Object(id=int(user_id)), reason=f"[{inter.user}] {reason}")
            await inter.response.send_message(f"✅ User `{user_id}` unbanned.")
            state.add_mod_action("unban", inter.user, user_id, reason, inter.guild.name)
        except discord.NotFound:
            await inter.response.send_message("🚫 That user is not banned.", ephemeral=True)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="timeout", description="Timeout a member for N minutes")
    @app_commands.describe(member="Member", minutes="Duration in minutes (1–40320)", reason="Reason")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, inter: discord.Interaction, member: discord.Member,
                      minutes: app_commands.Range[int, 1, 40320], reason: str = "No reason"):
        until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=minutes)
        try:
            await member.timeout(until, reason=f"[{inter.user}] {reason}")
            await inter.response.send_message(f"🔇 {member.mention} muted for **{minutes}m**. Reason: {reason}")
            state.add_mod_action("timeout", inter.user, member, f"{reason} ({minutes}m)", inter.guild.name)
            await _send_mod_log(inter.guild, "🔇 Member Timed Out",
                                f"**Member:** {member.mention}\n**Duration:** {minutes}m\n**Moderator:** {inter.user.mention}\n**Reason:** {reason}",
                                color=0xFEE75C)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="untimeout", description="Remove timeout from a member")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, inter: discord.Interaction, member: discord.Member):
        try:
            await member.timeout(None, reason=f"[{inter.user}] removed")
            await inter.response.send_message(f"🔊 {member.mention} unmuted.")
            state.add_mod_action("untimeout", inter.user, member, "", inter.guild.name)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="warn", description="Issue a warning to a member")
    @app_commands.default_permissions(kick_members=True)
    async def warn(self, inter: discord.Interaction, member: discord.Member, reason: str):
        count = storage.add_warning(inter.guild.id, member.id, inter.user.id, reason)
        embed = discord.Embed(title="⚠️ Warning Issued", color=0xFEE75C,
                              timestamp=datetime.datetime.utcnow())
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Total Warnings", value=str(count), inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.set_footer(text=f"By {inter.user}")
        await inter.response.send_message(embed=embed)
        state.add_mod_action("warn", inter.user, member, f"{reason} (total: {count})", inter.guild.name)
        try:
            await member.send(f"⚠️ You were warned in **{inter.guild.name}**.\nReason: {reason}")
        except Exception:
            pass

    @app_commands.command(name="warnings", description="View warnings for a member")
    async def warnings(self, inter: discord.Interaction, member: discord.Member = None):
        member = member or inter.user
        warns = storage.get_warnings(inter.guild.id, member.id)
        embed = discord.Embed(title=f"⚠️ Warnings for {member}", color=0xFEE75C)
        if not warns:
            embed.description = "No warnings on record."
        else:
            for i, w in enumerate(warns[-10:], 1):
                embed.add_field(name=f"#{i} — {w['time'][:10]}",
                                value=f"**Reason:** {w['reason']}\n**Mod ID:** `{w['moderator']}`",
                                inline=False)
            embed.set_footer(text=f"Total: {len(warns)} (showing last 10)")
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="clearwarns", description="Clear all warnings for a member")
    @app_commands.default_permissions(kick_members=True)
    async def clearwarns(self, inter: discord.Interaction, member: discord.Member):
        count = storage.clear_warnings(inter.guild.id, member.id)
        await inter.response.send_message(f"🧹 Cleared **{count}** warning(s) for {member.mention}.")
        state.add_mod_action("clear_warnings", inter.user, member, f"cleared {count}", inter.guild.name)

    @app_commands.command(name="purge", description="Bulk delete messages in this channel")
    @app_commands.describe(count="Number of messages (1–100)")
    @app_commands.default_permissions(manage_messages=True)
    async def purge(self, inter: discord.Interaction, count: app_commands.Range[int, 1, 100]):
        await inter.response.defer(ephemeral=True)
        deleted = await inter.channel.purge(limit=count)
        await inter.followup.send(f"🧹 Deleted **{len(deleted)}** messages.", ephemeral=True)
        state.add_mod_action("purge", inter.user, f"#{inter.channel.name}",
                             f"{len(deleted)} messages", inter.guild.name)

    @app_commands.command(name="slowmode", description="Set channel slowmode (0 to disable)")
    @app_commands.default_permissions(manage_channels=True)
    async def slowmode(self, inter: discord.Interaction, seconds: app_commands.Range[int, 0, 21600]):
        await inter.channel.edit(slowmode_delay=seconds)
        msg = "⏱️ Slowmode disabled." if seconds == 0 else f"⏱️ Slowmode set to **{seconds}s**."
        await inter.response.send_message(msg)
        state.add_mod_action("slowmode", inter.user, f"#{inter.channel.name}", f"{seconds}s", inter.guild.name)

    @app_commands.command(name="lock", description="Lock this channel for @everyone")
    @app_commands.default_permissions(manage_channels=True)
    async def lock(self, inter: discord.Interaction):
        ow = inter.channel.overwrites_for(inter.guild.default_role)
        ow.send_messages = False
        await inter.channel.set_permissions(inter.guild.default_role, overwrite=ow)
        await inter.response.send_message("🔒 Channel **locked**.")
        state.add_mod_action("lock", inter.user, f"#{inter.channel.name}", "", inter.guild.name)

    @app_commands.command(name="unlock", description="Unlock this channel for @everyone")
    @app_commands.default_permissions(manage_channels=True)
    async def unlock(self, inter: discord.Interaction):
        ow = inter.channel.overwrites_for(inter.guild.default_role)
        ow.send_messages = None
        await inter.channel.set_permissions(inter.guild.default_role, overwrite=ow)
        await inter.response.send_message("🔓 Channel **unlocked**.")
        state.add_mod_action("unlock", inter.user, f"#{inter.channel.name}", "", inter.guild.name)

    @app_commands.command(name="nick", description="Set or reset a member's nickname")
    @app_commands.default_permissions(manage_nicknames=True)
    async def nick(self, inter: discord.Interaction, member: discord.Member, nickname: str = ""):
        try:
            await member.edit(nick=nickname or None, reason=f"By {inter.user}")
            await inter.response.send_message(f"✏️ Nickname for {member.mention} set to **{nickname or 'reset'}**.")
            state.add_mod_action("nick", inter.user, member, nickname or "(reset)", inter.guild.name)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="addrole", description="Add a role to a member")
    @app_commands.default_permissions(manage_roles=True)
    async def addrole(self, inter: discord.Interaction, member: discord.Member, role: discord.Role):
        try:
            await member.add_roles(role, reason=f"By {inter.user}")
            await inter.response.send_message(f"✅ Added **{role.name}** to {member.mention}.")
            state.add_mod_action("addrole", inter.user, member, role.name, inter.guild.name)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)

    @app_commands.command(name="removerole", description="Remove a role from a member")
    @app_commands.default_permissions(manage_roles=True)
    async def removerole(self, inter: discord.Interaction, member: discord.Member, role: discord.Role):
        try:
            await member.remove_roles(role, reason=f"By {inter.user}")
            await inter.response.send_message(f"✅ Removed **{role.name}** from {member.mention}.")
            state.add_mod_action("removerole", inter.user, member, role.name, inter.guild.name)
        except discord.Forbidden:
            await inter.response.send_message("🚫 I lack permission.", ephemeral=True)
