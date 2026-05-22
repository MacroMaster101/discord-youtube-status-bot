"""Server-wide Discord events: joins, leaves, deletes, auto-mod."""
import time
import datetime
import collections
import discord
from discord.ext import commands
from config import Config
from core import state, storage

_spam_buckets = collections.defaultdict(lambda: collections.deque(maxlen=10))


async def _send_mod_log(guild, title, description, color=0xED4245):
    if not Config.MOD_LOG_CHANNEL_ID:
        return
    try:
        ch = guild.get_channel(int(Config.MOD_LOG_CHANNEL_ID))
        if ch is None:
            return
        embed = discord.Embed(title=title, description=description, color=color,
                              timestamp=datetime.datetime.utcnow())
        await ch.send(embed=embed)
    except Exception as e:
        state.add_log(f"mod-log send failed: {e}", "error")


def register(bot: commands.Bot):
    @bot.event
    async def on_member_join(member: discord.Member):
        if member.bot:
            return
        state.add_log(f"Member joined: {member.name} ({member.guild.name})", "info")
        channel = None
        if Config.WELCOME_CHANNEL_ID:
            channel = member.guild.get_channel(int(Config.WELCOME_CHANNEL_ID))
        if channel is None:
            channel = member.guild.system_channel
        if channel is None:
            return
        embed = discord.Embed(
            title="👋 Welcome to the server!",
            description=(
                f"Hey {member.mention}, welcome to **{member.guild.name}**! 🎉\n\n"
                f"📖 Use `/help` to see what I can do."
            ),
            color=0x57F287,
            timestamp=datetime.datetime.utcnow(),
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count}")
        await channel.send(embed=embed)

    @bot.event
    async def on_member_remove(member: discord.Member):
        state.add_log(f"Member left: {member.name} ({member.guild.name})", "info")
        await _send_mod_log(
            member.guild, "📤 Member Left",
            f"{member.mention} (`{member}`) left the server.", color=0x99AAB5,
        )

    @bot.event
    async def on_message_delete(message: discord.Message):
        if not message.guild or message.author.bot:
            return
        desc = (
            f"**Author:** {message.author.mention}\n"
            f"**Channel:** {message.channel.mention}\n"
            f"**Content:** {message.content[:1000] or '*(no text)*'}"
        )
        await _send_mod_log(message.guild, "🗑️ Message Deleted", desc, color=0xED4245)

    @bot.event
    async def on_message(message: discord.Message):
        if message.author.bot or not message.guild:
            return

        # Auto-moderation: spam
        if not message.author.guild_permissions.manage_messages:
            bucket = _spam_buckets[(message.guild.id, message.author.id)]
            now = time.time()
            bucket.append(now)
            recent = [t for t in bucket if now - t < Config.SPAM_WINDOW]
            if len(recent) >= Config.SPAM_THRESHOLD:
                try:
                    until = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=5)
                    await message.author.timeout(until, reason="Auto-mod: spam")
                    await message.channel.send(
                        f"🛡️ {message.author.mention} has been muted for 5 minutes (spam detected)."
                    )
                    state.add_mod_action("auto-timeout", "AutoMod", message.author, "Spam (5m)", message.guild.name)
                    await _send_mod_log(message.guild, "🛡️ Auto-Mod Timeout",
                                        f"{message.author.mention} timed out **5m** for spam.",
                                        color=0xFEE75C)
                    bucket.clear()
                except discord.Forbidden:
                    pass
                return

        # Friendly auto-responses
        content_lower = message.content.strip().lower().rstrip(".!?")
        if content_lower in {"gg", "gg wp", "ggwp", "good game"}:
            await message.channel.send(f"GG {message.author.mention}! 🏆🔥")
            try:
                await message.add_reaction("🏆")
            except Exception:
                pass

        # Let prefix commands still work (legacy aliases)
        await bot.process_commands(message)
