from discord.ext import commands
import discord

class Tags(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # self.coll = bot.plugin_db.get_partition(self)

    @commands.Cog.listener("on_message")
    async def temp_donos(self, message: discord.Message) -> None:
        if message.channel.id != 747853054329487500:
            return

        if message.content.lower() != "donos":
            return

        donos_embed = discord.Embed(title="Donation Guidelines", description="`**Donation Guidelines**\n`1.`  Please use this channel only for its intended purpose: making donations. (**No Begging**)\n`2.`  Prizes must be at least ⏣ 1,000,000.\n`3.`  Messages must abide by the <#658772308462141450>\n`4.`  Ping a giveaway manager. Once they are here, ask them if they can host your giveaway. __No spam pinging__.\n`5.`  State the message,winners and duration(1h minimum). If they can host it, donate to the server pool using the `/serverevents donate` command and let them host it for you!\n`6.`  Read the pins for more. ᵗʰᵃⁿᵏ ʸᵒᵘ ᵎᵎ `", colour=0x4f81d1)
        
        await ctx.send(embed=donos_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Tags(bot))
