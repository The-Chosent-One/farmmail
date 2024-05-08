import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel
import re


AMOUNT_MAP = {"k": "*1000", "m": "*1000000", "b": "*1000000000"}
AMOUNT_REGEX = re.compile(
    rf"^\d+(?:\.\d+)?[{''.join(AMOUNT_MAP)}]?$"
)
DONATION_ROLES = {
    1232708197035278468: 250_000_000,
    1232711148948947046: 500_000_000,
    1232711366775930961: 2_500_000_000,
    1232711901675389050: 5_000_000_000,
}

class Amount(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        match = AMOUNT_REGEX.search(argument)

        if match is None:
            raise commands.BadArgument("That doesn't seem like a number")

        amount = match.group(0)
        for suffix, replacement in AMOUNT_MAP.items():
            amount = amount.replace(suffix, replacement)

        res: int | float = compile(amount, "", "eval").co_consts[0]

        if isinstance(res, float) and not res.is_integer():
            raise commands.BadArgument("That doesn't seem like a number")

        return int(res)

class DonationTracking(commands.Cog):
    """
    Keeps track of dank doantions for members
    """
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    async def add_coins(self, donator_id: int, coins: int) -> None:
        await self.coll.update_one({"user_id": donator_id}, {"$inc": {"dank_coins": coins}}, upsert=True)

    async def remove_coins(self, donator_id: int, coins: int) -> None:
        await self.coll.update_one({"user_id": donator_id}, {"$inc": {"dank_coins": -coins}}, upsert=True)
    
    async def get_coins(self, donator_id: int) -> int | None:
        res = await self.coll.find_one({"user_id": donator_id})

        if res is None:
            return None
        
        return res["dank_coins"]

    async def add_new_dono_roles(self, donator: discord.Member) -> None:
        current_coins = await self.get_coins(donator.id)
        for role_id, donation_amount in DONATION_ROLES.items():
            if donator._roles.has(role_id):
                continue

            if current_coins >= donation_amount:
                await donator.add_roles(discord.Object(id=role_id))

    async def remove_new_dono_roles(self, donator: discord.Member) -> None:
        current_coins = await self.get_coins(donator.id)
        for role_id, donation_amount in DONATION_ROLES.items():
            if donator._roles.has(role_id) and current_coins < donation_amount:
                await donator.remove_roles(discord.Object(id=role_id))

    async def get_donation_embed(self, donator: discord.Member, amount: int = None) -> discord.Embed:
        if amount is None:
            amount = await self.get_coins(donator.id)

        donation = discord.Embed(title=f"{donator.name}'s donation", description=f"> Total donations: **⏣ {amount:,}**", colour=0x5865f2)
        donation.set_footer(text="Thank you for donating!")

        return donation
    
    @commands.group(invoke_without_command=True, aliases=["dd"])
    async def dankdonor(self, ctx: commands.Context) -> None:
        """Dank donation commands."""
        return
    
    @dankdonor.command()
    @commands.check_any(
        checks.has_permissions(PermissionLevel.MODERATOR),
        commands.has_role(855877108055015465) # Giveaway Manager
    )
    async def add(self, ctx: commands.Context, donator: discord.Member, amount: Amount) -> None:
        """Add a dank donation to a member."""
        await self.add_coins(donator.id, amount)
        await self.add_new_dono_roles(donator)
        
        donation = await self.get_donation_embed(donator)
        await ctx.reply(f"Added **⏣ {amount:,}** to {donator.name}", embed=donation)
    
    @dankdonor.command()
    @commands.check_any(
        checks.has_permissions(PermissionLevel.MODERATOR),
        commands.has_role(855877108055015465) # Giveaway Manager
    )
    async def remove(self, ctx: commands.Context, donator: discord.Member, amount: Amount) -> None:
        """Remove a donation amount from a member."""
        current_amount = await self.get_coins(donator.id)

        if current_amount is None:
            return await ctx.reply(f"{donator.name} has not donated anything yet")

        if amount > current_amount:
            return await ctx.reply(f"{donator.name} does not have that much to remove")

        donation = await self.get_donation_embed(donator, amount=current_amount-amount)
        
        await self.remove_coins(donator.id, amount)
        await self.remove_new_dono_roles(donator)
        await ctx.reply(f"Removed **⏣ {amount:,}** from {donator.name}", embed=donation)
    
    @dankdonor.command()
    async def view(self, ctx: commands.Context, member: discord.Member = None) -> None:
        """View dank donations of a member."""
        target = member or ctx.author
        donator_id = target.id

        amount = await self.get_coins(donator_id)

        if amount is None:
            return await ctx.reply(f"{target.name} has not donated yet")

        donation = await self.get_donation_embed(target, amount=amount)
        await ctx.reply(embed=donation)

    @dankdonor.command(aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context) -> None:
        """View the top donors in The Farm."""
        res = await self.coll.find().sort({"dank_coins": -1}).to_list(10)

        embed = discord.Embed(title="Top 10 donors in The Farm", description="", colour=0x5865f2)

        for number, entry in enumerate(res, start=1):
            user_id, donated = entry["user_id"], entry["dank_coins"]
            medals = {1: ":first_place:", 2: ":second_place:", 3: ":third_place:"}
    
            if number in medals:
                embed.description += f"{medals[number]} "
            else:
                embed.description += f"{number}) "
            embed.description += f"<@{user_id}> - **⏣ {donated:,}**\n"
        
        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))
