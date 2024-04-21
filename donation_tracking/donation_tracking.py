from discord.ext import commands
import discord

class DonationTracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    @commands.Cog.listener("on_message")
    async def donation_track(self, message: discord.Message) -> None:
        if message.author.id != 270904126974590976:
            return

        if message.channel.id != 1022489369954758696:
            return

        if message.embeds == []:
            return                

        await message.channel.send(message.embeds[0])
    
    @commands.command(hidden=True)
    async def get_embed(self, ctx: commands.Context, message_id: int):
        if ctx.author.id != 531317158530121738:
            return
        
        msg = await ctx.channel.fetch_message(message_id)

        await ctx.send(msg.embeds[0])



async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))