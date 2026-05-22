"""Fun slash commands: roll, flip, 8ball, rps, poll."""
import datetime
import random
import discord
from discord import app_commands
from discord.ext import commands

EIGHT_BALL = [
    "🟢 Yes, definitely!", "🟢 Without a doubt.", "🟢 It is certain.",
    "🟢 Most likely.", "🟢 Yes!", "🟢 Outlook good.",
    "🟡 Ask again later.", "🟡 Hard to say.", "🟡 Cannot predict now.",
    "🔴 Don't count on it.", "🔴 My sources say no.", "🔴 Very doubtful.",
]

RPS_EMOJIS = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="roll", description="Roll a dice")
    async def roll(self, inter: discord.Interaction, sides: app_commands.Range[int, 2, 1000] = 6):
        result = random.randint(1, sides)
        await inter.response.send_message(f"🎲 {inter.user.mention} rolled a **{result}** (1-{sides})")

    @app_commands.command(name="flip", description="Flip a coin")
    async def flip(self, inter: discord.Interaction):
        result = random.choice(["🪙 **Heads!**", "🪙 **Tails!**"])
        await inter.response.send_message(f"{inter.user.mention} flipped: {result}")

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    async def eight_ball(self, inter: discord.Interaction, question: str):
        embed = discord.Embed(title="🎱 Magic 8-Ball", color=0x2B2D31)
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(EIGHT_BALL), inline=False)
        embed.set_footer(text=f"Asked by {inter.user}")
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="rps", description="Play rock-paper-scissors")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Rock", value="rock"),
        app_commands.Choice(name="Paper", value="paper"),
        app_commands.Choice(name="Scissors", value="scissors"),
    ])
    async def rps(self, inter: discord.Interaction, choice: app_commands.Choice[str]):
        user_choice = choice.value
        bot_choice = random.choice(list(RPS_EMOJIS))
        if user_choice == bot_choice:
            result = "🤝 It's a **tie**!"
        elif (user_choice, bot_choice) in {("rock", "scissors"), ("paper", "rock"), ("scissors", "paper")}:
            result = "🎉 You **win**!"
        else:
            result = "😎 I **win**!"
        embed = discord.Embed(title="Rock Paper Scissors", color=0xFEE75C)
        embed.add_field(name="You", value=f"{RPS_EMOJIS[user_choice]} {user_choice.title()}", inline=True)
        embed.add_field(name="Bot", value=f"{RPS_EMOJIS[bot_choice]} {bot_choice.title()}", inline=True)
        embed.add_field(name="Result", value=result, inline=False)
        await inter.response.send_message(embed=embed)

    @app_commands.command(name="poll", description="Create a quick reaction poll")
    async def poll(self, inter: discord.Interaction, question: str):
        embed = discord.Embed(title="📊 Poll", description=question, color=0x5865F2,
                              timestamp=datetime.datetime.utcnow())
        embed.set_footer(text=f"Poll by {inter.user}")
        await inter.response.send_message(embed=embed)
        msg = await inter.original_response()
        for emoji in ("👍", "👎", "🤷"):
            await msg.add_reaction(emoji)
