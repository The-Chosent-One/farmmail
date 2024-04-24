from discord.ext import commands
from contextlib import redirect_stdout
import io
import traceback
import textwrap
import discord
import re

class DonationTracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)
        self.coins_re = re.compile(r"\d+(?:,\d+)*")
        self.items_re = re.compile(r"(\d+(?:,\d+)*).+?: (.*)\*\*")

    @commands.Cog.listener("on_message")
    async def donation_track(self, message: discord.Message) -> None:
        if message.author.id != 270904126974590976:
            return

        if message.embeds == []:
            return

        if message.channel.id != 1022489369954758696:
            return

        if "Are you sure you want to donate your items?" not in message.embeds[0].description:
            return
            
        # if message.embeds[0].description != "Successfully donated!":
        #     return
        
        # original = message.reference.cached_message or message.reference.resolved

        # if isinstance(original, discord.DeletedReferencedMessage):
        #     return

        # if original is None:
        #     original = await message.channel.fetch_message(message.reference.message_id)

        original = message
        donator_id = original.interaction.user.id
        donation_msg = original.embeds[0].description
        
        if "⏣" in donation_msg:
            coins_donated = int(self.coins_re.findall(donation_msg)[0].replace(",", "_"))
            self.coll.update_one({"user_id": donator_id}, {"$inc", {"dank_coins": coins_donated}}, upsert=True)
            await message.channel.send(f"You have donated ⏣ {coins_donated}... I think")

        else:
            number_of_items, item = self.items_re.findall(donation_msg)
            number_of_items = int(number_of_items.replace(",", "_"))
            self.coll.update_one({"user_id": donator_id}, {"$inc", {f"items.{item}": number_of_items}}, upsert=True)
            await message.channel.send(f"You have donated {number_of_items} {item}... hopefully")

async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))
