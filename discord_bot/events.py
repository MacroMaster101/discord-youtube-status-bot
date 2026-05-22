"""Server events: welcome new members + friendly GG auto-response."""
import datetime
import discord
from discord.ext import commands
from config import Config
from core import state


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
            title="👋 Welcome!",
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
    async def on_message(message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content_lower = message.content.strip().lower().rstrip(".!?")
        if content_lower in {"gg", "gg wp", "ggwp", "good game"}:
            await message.channel.send(f"GG {message.author.mention}! 🏆🔥")
            try:
                await message.add_reaction("🏆")
            except Exception:
                pass
        await bot.process_commands(message)
