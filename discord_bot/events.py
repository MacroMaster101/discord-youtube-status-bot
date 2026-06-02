"""Server events: welcome new members + friendly GG auto-response."""
import datetime
import discord
from discord.ext import commands
from config import Config
from core import state


def register(bot: commands.Bot):
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
