from discord.ext import commands
from contextlib import redirect_stdout
import io
import traceback
import textwrap
import discord

class DonationTracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    @commands.Cog.listener("on_message")
    async def donation_track(self, message: discord.Message) -> None:
        if message.author.id != 270904126974590976:
            return

        if message.embeds == []:
            return

        if message.embeds[0].description != "Successfully donated!":
            return

        if message.channel.id != 1022489369954758696:
            return

        original = message.reference.cached_message or message.reference.resolved

        if isinstance(original, discord.DeletedReferencedMessage):
            return

        if original is None:
            original = await message.channel.fetch_message(message.reference.message_id)

        await message.channel.send(original.embeds[0].description)

    @commands.command(hidden=True)
    async def donation_test(self, ctx: commands.Context) -> None:
        if ctx.author.id != 531317158530121738:
            return

        await ctx.send("It's working!!")


async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))
