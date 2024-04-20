import traceback
import discord
import re
from .currency_core import CurrencyHandler
from .currency_data import LEVEL_INCOMES, BOOSTER_INCOMES, CASH_INCOMES
from discord.ext import commands
from math import ceil
from motor import motor_asyncio
from time import time
from core import checks
from core.models import PermissionLevel

AMOUNT_MAP = {"k": "*1000", "m": "*1000000", "b": "*1000000000"}
AMOUNT_REGEX = re.compile(
    rf"^-?\d+(?:(?:\.\d+)?[{''.join(AMOUNT_MAP)}]|(?:\.\d+)?e\d+)?$"
)


class Amount(commands.Converter):
    async def convert(self, ctx: commands.Context, argument: str) -> int:
        match = AMOUNT_REGEX.search(argument)

        if match is None:
            raise commands.BadArgument("Converting failed")

        amount = match.group(0)
        for suffix, replacement in AMOUNT_MAP.items():
            amount = amount.replace(suffix, replacement)

        res: int | float = compile(amount, "", "eval").co_consts[0]

        if isinstance(res, float) and not res.is_integer():
            raise commands.BadArgument("Converting failed")

        return int(res)


class Currency(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        collection: motor_asyncio.AsyncIOMotorCollection = bot.plugin_db.get_partition(
            self
        )
        self.currency_handler = CurrencyHandler(self.bot, collection)
        self.emoji = "<:farm_zzcash:927739006899335188>"

    async def cog_check(self, ctx: commands.Context) -> bool:
        if ctx.channel.id != 789809104738189342:
            return False
        return True

    async def change_cash(self, target: discord.Member, cash: int) -> discord.Embed:
        updated_cash = await self.currency_handler.update_cash(target, cash=cash)

        embed = discord.Embed(title=f"Success!")
        embed.description = (
            f"{target}'s balance is now: \n"
            f"` - ` Cash: {self.emoji} **{updated_cash:,}**"
        )
        return embed

    @commands.Cog.listener(name="on_message")
    async def on_vote(self, message: discord.Message) -> None:
        if message.channel.id == 995427147038601306:
            if message.mentions:
                target = message.mentions[0]
                await self.currency_handler.update_cash(target, cash=1)

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def addcash(self, ctx, target: discord.Member, cash: Amount):
        if cash < 0:
            return await ctx.reply("Use `??removecash` instead")

        await ctx.send(embed=await self.change_cash(target, cash))

    @addcash.error
    async def addcash_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("Correct usage:\n```??addcash <member> <amount>```")
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(
                "You keyed in an invalid user or the user is not in the guild"
            )
        if isinstance(error, commands.BadArgument):
            return await ctx.reply("That's not an integer")

        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def removecash(self, ctx, target: discord.Member, cash: Amount):
        if cash < 0:
            return await ctx.reply("Use `??addcash` instead")

        await ctx.send(embed=await self.change_cash(target, -cash))

    @removecash.error
    async def removecash_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply(
                "Correct usage:\n```??removecash <member> <amount>```"
            )
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(
                "You keyed in an invalid user or the user is not in the guild"
            )
        if isinstance(error, commands.BadArgument):
            return await ctx.reply("That's not an integer")

        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def setcash(
        self, ctx: commands.Context, target: discord.Member, cash: Amount
    ):
        updated_cash = await self.currency_handler.set_cash(target, cash=cash)

        embed = discord.Embed(title=f"Success!")
        embed.description = (
            f"{target}'s balance is now: \n"
            f"` - ` Cash: {self.emoji} **{updated_cash:,}**"
        )

        await ctx.send(embed=embed)

    @setcash.error
    async def setcash_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, commands.BadArgument):
            return await ctx.reply("That's not an integer")
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("Correct usage:\n```??setcash <member> <amount>```")
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(
                "You keyed in an invalid user or the user is not in the guild"
            )

        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.command(aliases=["give"])
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def share(
        self, ctx: commands.Context, target: discord.Member, amount: Amount
    ) -> None:
        if amount < 0:
            return await ctx.reply("That won't work :>")

        if amount == 0:
            return await ctx.reply("Then why..?")

        if amount >= 2147483648:
            return await ctx.reply("🧢 no way you have that much")

        cash = await self.currency_handler.get_cash(ctx.author)

        tax = ceil(0.15 * amount)
        required = amount + tax

        if required > cash:
            embed = discord.Embed(
                title="You're too broke ⍨",
                description=f"You only have {self.emoji} **{cash:,}**\n(And cannot pay {self.emoji} **{amount:,}** + {self.emoji} **{tax:,}** in taxes)",
                colour=0xEB3434,
            )
            embed.set_footer(text="Tax amount is 15%")
            return await ctx.reply(embed=embed)

        await self.currency_handler.update_cash(target, cash=amount)
        await self.currency_handler.update_cash(ctx.author, cash=-required)

        embed = discord.Embed(
            title="Shared coins!",
            description=f"Paid {self.emoji} **{amount:,}** + {self.emoji} **{tax:,}** (in taxes) to {target.mention}!",
            colour=0x49EB34,
        )
        embed.set_footer(text="Tax amount is 15%")
        await ctx.reply(embed=embed)

    @share.error
    async def share_error(self, ctx: commands.Context, error) -> None:
        if isinstance(error, commands.MissingRequiredArgument):
            return await ctx.reply("Correct usage:\n`??share <member> <amount>`")
        if isinstance(error, commands.MemberNotFound):
            return await ctx.reply(
                "You keyed in an invalid user or the user is not in the guild"
            )
        if isinstance(error, commands.BadArgument):
            return await ctx.reply("That's not an integer")

        traceback.print_exception(type(error), error, error.__traceback__)

    @commands.command(alias=["bal"])
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def balance(self, ctx: commands.Context) -> None:
        cash = await self.currency_handler.get_cash(ctx.author)

        embed = discord.Embed(
            title=f"{ctx.author}'s balance",
            description=f"Cash: {self.emoji} **{cash:,}**",
        )
        await ctx.reply(embed=embed)

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def income(self, ctx: commands.Context) -> None:
        next_income_time = await self.currency_handler.get_next_income_time(ctx.author)

        if next_income_time is not None and time() < next_income_time:
            embed = discord.Embed(
                title="Income cooldown",
                description=f"You can claim your income in <t:{next_income_time}:R>",
            )
            return await ctx.reply(embed=embed)

        # level income, booster income, cash income
        income_groups = [0, 0, 0]

        for index, income_data in enumerate(
            [LEVEL_INCOMES, BOOSTER_INCOMES, CASH_INCOMES]
        ):
            for role_id, income in income_data.items():
                if ctx.author._roles.has(role_id):
                    income_groups[index] = max(income, income_groups[index])

        total_income = sum(income_groups)

        if total_income == 0:
            embed = discord.Embed(
                title="Income collection",
                description="You don't have any income to claim :(",
            )
            return await ctx.reply(embed=embed)

        await self.currency_handler.update_cash(ctx.author, total_income)

        next_time = round(time()) + 604800  # amount of seconds in a week
        await self.currency_handler.update_income_time(ctx.author, next_time)

        embed = discord.Embed(
            title="Income collection",
            description=f"You collected {self.emoji} **{total_income:,}**!",
        )
        await ctx.reply(embed=embed)

    @income.error
    async def income_error(self, ctx: commands.Context, error) -> None:
        traceback.print_exception(type(error), error, error.__traceback__)


async def setup(bot):
    await bot.add_cog(Currency(bot))
