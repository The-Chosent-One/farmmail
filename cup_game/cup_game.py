from discord.ext import commands
import discord
import asyncio
import random
from core import checks
from core.models import PermissionLevel


class Start(discord.ui.View):
    def __init__(self, gamers: set[int], host_id: int) -> None:
        self.gamers = gamers
        self.host_id = host_id
        self.cancelled = False
        # for killing the current view
        self.current_view = self
        # set later
        self.message: discord.Message = None
        super().__init__(timeout=None)

    async def stop_game(self) -> None:
        for view in {self, self.current_view}:
            for item in view.children:
                item.disabled = True
            await view.message.edit(view=view)
            view.stop()

    async def cancel_game(self, interaction: discord.Interaction) -> None:
        self.cancelled = True
        await self.stop_game()
        can_embed = discord.Embed(
            title="Game cancelled!",
            description="The game has been cancelled by the host",
            color=discord.Color.red(),
        )
        await interaction.response.send_message(embed=can_embed)

    @discord.ui.button(label="Join game", style=discord.ButtonStyle.success)
    async def join_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user.id in self.gamers:
            return await interaction.response.send_message(
                "You've already joined the game", ephemeral=True
            )
        self.gamers[interaction.user.id] = 0
        await interaction.response.send_message(
            "You've successfully joined the game!", ephemeral=True
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        if interaction.user.id != self.host_id:
            return await interaction.response.send_message(
                "Only the host can cancel the game", ephemeral=True
            )
        await self.cancel_game(interaction)


class cupButton(discord.ui.Button):
    def __init__(self, correct_cup: bool) -> None:
        self.correct_cup = correct_cup
        super().__init__(emoji="🥤", style=discord.ButtonStyle.grey, disabled=False)

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id in self.view.clicked_ids:
            return await interaction.response.send_message(
                "You have chosen your cup already", ephemeral=True
            )
        if self.correct_cup:
            self.view.gamers[interaction.user.id] += 1
        self.view.clicked_ids.add(interaction.user.id)
        await interaction.response.send_message(
            "You have selected a cup... but is it the correct one?", ephemeral=True
        )


class roundView(discord.ui.View):
    def __init__(self, gamers: dict, cups: int):
        self.gamers = gamers
        self.clicked_ids = set()
        # set later
        self.message = None
        super().__init__(timeout=None)
        self.add_items(cups)

    def add_items(self, cups: int):
        lucky_cup = random.randrange(cups)
        for cup in range(cups):
            self.add_item(cupButton(cup == lucky_cup))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.gamers:
            await interaction.response.send_message(
                "You haven't joined the game!", ephemeral=True
            )
            return False
        return True

    async def end_round(self) -> None:
        for item in self.children:
            if item.correct_cup:
                item.style = discord.ButtonStyle.success
            item.disabled = True
        await self.message.edit(view=self)


class cupGame(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def send_scores(
        self, ctx: commands.Context, gamers: dict, last_round: bool
    ) -> None:
        scores_message = "# The round has ended"
        scores_embed = discord.Embed(
            title="**Current scores:**", color=discord.Color.blue()
        )
        scores_embed.description = "\n".join(
            f"<@{id}> - {points}" for id, points in gamers.items()
        )
        scores_embed.set_footer(text="The next round will start in 5 seconds")

        if last_round:
            scores_message = "# The game has ended"
            scores_embed.title = "**Final scores:**"
            scores_embed.remove_footer()

        await ctx.send(scores_message, embed=scores_embed)

    @commands.command(aliases=["cg"])
    @commands.check_any(
        checks.has_permissions(PermissionLevel.MODERATOR),
        commands.has_role(855877108055015465),  # Giveaway Manager
    )
    async def cupgame(self, ctx: commands.Context, cups: int, rounds: int):
        """Play a game of chance with some cups, created for the use in events/giveaways"""
        if cups < 0 or rounds < 0:
            return await ctx.reply("Neither of those can be negative")
        if rounds == 0 or cups == 0:
            return await ctx.reply("You can't play with 0 rounds or cups")
        if cups == 1:
            return await ctx.reply("You can't play a game with only one cup")
        if rounds == 1:
            return await ctx.reply("Minimum of 2 rounds are required")
        if cups > 25:
            return await ctx.reply("You can only pick a maximum of 25 cups")
        if rounds > 50:
            return await ctx.reply("Why would you want that many rounds")

        start_embed = discord.Embed(
            title="Which cup has the coin?",
            description=f"**Rules:**\n\n - From {cups} cups you have to click on a cup which you think has the coin.\n - You can choose 1 option only.\n - For each round, `20 seconds` is given.\n - If you guess correctly you earn 1 point.\n - Person with maximum points after {rounds} rounds wins!\n - Game starts after 30s.",
            colour=0x5865F2,
        )

        gamers = {}
        start_view = Start(gamers, host_id=ctx.author.id)
        await ctx.message.delete()
        message = await ctx.send(embed=start_embed, view=start_view)
        start_view.message = message

        await asyncio.sleep(30)

        if start_view.cancelled:
            return

        if len(gamers) < 1:
            await start_view.stop_game()
            return await message.reply("Not enough people joined :pensive:")

        start_view.children[0].disabled = True
        await message.edit(view=start_view)

        players_embed = discord.Embed(
            title="All players that joined:",
            description=f"**Total players:** {len(gamers)}\n",
            color=discord.Color.green(),
        )
        players_embed.description += "\n".join(f"<@{id}>" for id in gamers)
        players_embed.set_footer(text="Game starting in 10 seconds!")
        await ctx.send(embed=players_embed)
        await asyncio.sleep(10)

        if start_view.cancelled:
            return

        for round_number in range(1, rounds + 1):
            round_view = roundView(gamers, cups)
            round_embed = discord.Embed(
                title=f"Which cup has the coin?",
                description=f"Round {round_number} of {rounds}",
                colour=0x5865F2,
            )
            round_embed.set_footer(text="Round is ending in 20 seconds")
            message = await ctx.send(embed=round_embed, view=round_view)
            round_view.message = message
            start_view.current_view = round_view

            await asyncio.sleep(20)
            if start_view.cancelled:
                return
            await round_view.end_round()

            gamers = dict(sorted(gamers.items(), key=lambda i: i[1], reverse=True))

            last_round = round_number == rounds
            await self.send_scores(ctx, gamers, last_round)

            if not last_round:
                await asyncio.sleep(5)

            if start_view.cancelled:
                return

        await start_view.stop_game()


async def setup(bot: commands.Bot):
    await bot.add_cog(cupGame(bot))
