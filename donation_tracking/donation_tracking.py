import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

class DonationTracking(commands.Cog):
    """
    Keeps track of dank doantions for members
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    async def add_coins(self, donator_id: int, coins: int) -> None:
        await self.coll.update_one({"user_id": donator_id}, {"$inc": {"dank_coins": coins}}, upsert=True)
    
    async def get_coins(self, donator_id: int) -> int | None:
        res = await self.coll.find_one({"user_id": donator_id})

        if res is None:
            return None
        
        return res["dank_coins"]
    
    @commands.group(invoke_without_command=True, aliases=["dd"])
    async def dankdonor(self, ctx: commands.Context) -> None:
        """Dank donation commands."""
        return
    
    @dankdonor.command()
    @commands.check_any(
        checks.has_permissions(PermissionLevel.ADMIN),
        commands.has_role(855877108055015465) # Giveaway Manager
    )
    async def add(self, ctx: commands.Context, member: discord.Member, amount: int) -> None:
        """Add a dank donation to a member."""
        await self.add_coins(member.id, amount)
        await ctx.reply(f"Added **⏣ {amount:, }** to {member.name}")
    
    @dankdonor.command()
    async def view(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """View dank donations of a member."""
        target = member or ctx.author
        donator_id = target.id

        amount = await self.get_coins(donator_id)

        if amount is None:
            return await ctx.reply(f"{target.name} has not donated yet")

        donation = discord.Embed(title=f"{target.name}'s donation", description=f"> Donated: **⏣ {amount:,}**", colour=0x5865f2)
        donation.set_footer(text="Thank you for donating!")
        await ctx.reply(embed=donation)


async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))
