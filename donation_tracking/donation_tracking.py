import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel
import re


AMOUNT_MAP = {"k": "*1000", "m": "*1000000", "b": "*1000000000"}
AMOUNT_REGEX = re.compile(rf"^\d+(?:\.\d+)?[{''.join(AMOUNT_MAP)}]?$")
DONATION_ROLES = {
    1232708197035278468: 250_000_000,
    1232711148948947046: 500_000_000,
    1232711366775930961: 2_500_000_000,
    1232711901675389050: 5_000_000_000,
    1271897706087973005: 10_000_000_000,
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
        await self.coll.update_one(
            {"user_id": donator_id}, {"$inc": {"dank_coins": coins}}, upsert=True
        )

    async def remove_coins(self, donator_id: int, coins: int) -> None:
        await self.coll.update_one(
            {"user_id": donator_id}, {"$inc": {"dank_coins": -coins}}, upsert=True
        )

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

    async def get_donation_embed(
        self, donator: discord.Member | discord.User, amount: int = None
    ) -> discord.Embed:
        if amount is None:
            amount = await self.get_coins(donator.id)

        donation = discord.Embed(
            title=f"{donator.name}'s donation",
            description=f"> Total donations: **⏣ {amount:,}**",
            colour=0x5865F2,
        )
        
        if isinstance(donator, discord.Member):
            donation.set_footer(text="Thank you for donating!")
        else:
            donation.set_footer(text="This user is not in this server")

        return donation

    @commands.group(invoke_without_command=True, aliases=["dd"])
    async def dankdonor(self, ctx: commands.Context) -> None:
        """Dank donation commands."""
        await ctx.send_help(ctx.command)

    @dankdonor.command()
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def add(
        self, ctx: commands.Context, donator: discord.Member | discord.User, amount: Amount
    ) -> None:
        """Add a dank donation to a member."""
        # since we can't commands.check_any with a PermissionLevel.MODERATOR and commands.has_role, 
        # we allow all staff roles to access this command, but filter the staff roles except Giveaway Manager
        # This basically allows the union of PermissionLevel.MODERATOR and Giveaway Managers
        if sum(map(ctx.author._roles.has, [723035638357819432, 814004142796046408, 790290355631292467])) and not ctx.author._roles.has(855877108055015465):
            return

        current_amount = await self.get_coins(donator.id)
        if not isinstance(donator, discord.Member) and current_amount is None:
            raise commands.BadArgument(f'Member "{donator}" not found')

        await self.add_coins(donator.id, amount)
        if isinstance(donator, discord.Member):
            await self.add_new_dono_roles(donator)

        donation = await self.get_donation_embed(donator)
        await ctx.reply(f"Added **⏣ {amount:,}** to {donator.name}", embed=donation)

    @dankdonor.command()
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def remove(
        self, ctx: commands.Context, donator: discord.Member | discord.User, amount: Amount
    ) -> None:
        """Remove a donation amount from a member."""
        if sum(map(ctx.author._roles.has, [723035638357819432, 814004142796046408, 790290355631292467])) and not ctx.author._roles.has(855877108055015465):
            return
        
        current_amount = await self.get_coins(donator.id)

        if not isinstance(donator, discord.Member) and current_amount is None:
            raise commands.BadArgument(f'Member "{donator}" not found')

        if current_amount is None:
            return await ctx.reply(f"{donator.name} has not donated anything yet")

        if amount > current_amount:
            return await ctx.reply(f"{donator.name} does not have that much to remove")

        donation = await self.get_donation_embed(
            donator, amount=current_amount - amount
        )

        await self.remove_coins(donator.id, amount)
        if isinstance(donator, discord.Member):
            await self.remove_new_dono_roles(donator)
        await ctx.reply(f"Removed **⏣ {amount:,}** from {donator.name}", embed=donation)

    @dankdonor.command()
    async def view(self, ctx: commands.Context, member: discord.Member | discord.User = None) -> None:
        """View dank donations of a member."""
        target = member or ctx.author
        donator_id = target.id

        amount = await self.get_coins(donator_id)

        if not isinstance(target, discord.Member) and amount is None:
            raise commands.BadArgument(f'Member "{target}" not found')

        if amount is None:
            return await ctx.reply(f"{target.name} has not donated yet")

        donation = await self.get_donation_embed(target, amount=amount)
        await ctx.reply(embed=donation)

    @dankdonor.command(aliases=["olb"])
    async def overallleaderboard(self, ctx: commands.Context) -> None:
        """View the top overall donors in The Farm."""
        res = await self.coll.find().sort({"dank_coins": -1}).to_list(10)

        embed = discord.Embed(
            title="Top 10 donors in The Farm", description="", colour=0x5865F2
        )

        for number, entry in enumerate(res, start=1):
            user_id, donated = entry["user_id"], entry["dank_coins"]
            medals = {1: ":first_place:", 2: ":second_place:", 3: ":third_place:"}

            if number in medals:
                embed.description += f"{medals[number]} "
            else:
                embed.description += f"{number}) "
            embed.description += f"<@{user_id}> - **⏣ {donated:,}**\n"

        await ctx.reply(embed=embed)

    @dankdonor.command(aliases=["slb"])
    async def serverleaderboard(self, ctx: commands.Context) -> None:
        """View the top donors currently in the server."""
        embed = discord.Embed(
            title="Top 10 donors in The Farm", description="", colour=0x5865F2
        )

        number = 1
        async for entry in self.coll.find().sort({"dank_coins": -1}):
            user_id, donated = entry["user_id"], entry["dank_coins"]
            
            if ctx.bot.guild.get_member(user_id) is None:
                continue

            medals = {1: ":first_place:", 2: ":second_place:", 3: ":third_place:"}

            if number in medals:
                embed.description += f"{medals[number]} "
            else:
                embed.description += f"{number}) "
            embed.description += f"<@{user_id}> - **⏣ {donated:,}**\n"
            
            number += 1
            if number > 10:
                break
                
        embed.set_footer(text="Users in The Farm")

        await ctx.reply(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))
