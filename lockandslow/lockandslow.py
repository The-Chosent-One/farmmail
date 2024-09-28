import discord
import re
from discord.ext import commands
from datetime import timedelta

ALLOWED_CHANNELS = {
    995563300618240100, # 🎲┃event-room¹
    995563935874949160, # 🎲┃event-room²
    756552586248585368, # 💲┃mafia-lobby
    747853054329487500, # 🎁┃donate-here
    1150860516349190144, # 🎫┃lottery-entries
}

GIVEAWAY_MANAGER = 855877108055015465
CHAT_MOD = 814004142796046408
MODERATOR = 682698693472026749
HEAD_MODERATOR = 658770981816500234
SERVER_ADMIN = 663162896158556212
FARM_OWNER = 658770586540965911


def to_seconds(s):
    return int(
        timedelta(
            **{
                {
                    "s": "seconds",
                    "m": "minutes",
                    "h": "hours",
                    "d": "days",
                    "w": "weeks",
                }.get(m.group("unit").lower(), "seconds"): int(m.group("val"))
                for m in re.finditer(r"(?P<val>\d+)(?P<unit>[smhdw]?)", s, flags=re.I)
            }
        ).total_seconds()
    )


class LockAndSlow(commands.Cog):
    """
    Lock/Unlock and slowmode channels
    """

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_any_role(GIVEAWAY_MANAGER, CHAT_MOD, MODERATOR, HEAD_MODERATOR, SERVER_ADMIN, FARM_OWNER)
    async def lock(self, ctx, channel: discord.TextChannel = None):
        """
        Lock a channel
        """
        if channel is None:
            channel = ctx.channel

        if not {MODERATOR, HEAD_MODERATOR, SERVER_ADMIN, FARM_OWNER} & set(ctx.author._roles) and channel.id not in ALLOWED_CHANNELS:
            return await ctx.send(f"You are not allowed to lock {channel}")

        if (
            channel.overwrites_for(ctx.guild.default_role).send_messages is None
            or channel.overwrites_for(ctx.guild.default_role).send_messages
            is True
        ):
            await channel.set_permissions(
                ctx.guild.default_role, send_messages=False
            )
            await ctx.send(f"🔒 Locked `{channel}`")
        else:
            await ctx.send(f"🔒 Looks like `{channel}` is already locked")

    @commands.command()
    @commands.has_any_role(GIVEAWAY_MANAGER, CHAT_MOD, MODERATOR, HEAD_MODERATOR, SERVER_ADMIN, FARM_OWNER)
    async def unlock(self, ctx, channel: discord.TextChannel = None):
        """
        Unlock a channel
        """
        if channel is None:
            channel = ctx.channel

        if not {MODERATOR, HEAD_MODERATOR, SERVER_ADMIN, FARM_OWNER} & set(ctx.author._roles) and channel.id not in ALLOWED_CHANNELS:
            return await ctx.send(f"You are not allowed to unlock {channel}")

        if not channel.overwrites_for(ctx.guild.default_role).send_messages:
            await channel.set_permissions(
                ctx.guild.default_role, send_messages=True
            )
            await ctx.send(f"🔒 Unlocked `{channel}`")
        else:
            await ctx.send(f"🔒 Looks like `{channel}` is already unlocked")

    @commands.command(aliases=["slowmode", "slow"])
    @commands.has_permissions(manage_messages=True)
    async def sm(self, ctx, delay):
        """
        Set slowmode for a channel
        """
        slomo_embed = discord.Embed(
            title=f" A slowmode of {delay} has been activated by a moderator.",
            color=0x363940,
            timestamp=ctx.message.created_at,
        )
        slomo_embed.set_footer(
            text=f"Applied by {ctx.author}", icon_url=ctx.author.avatar
        )
        await ctx.message.delete()
        await ctx.channel.edit(slowmode_delay=to_seconds(delay))
        await ctx.send(content=None, embed=slomo_embed)

    @commands.command()
    async def slownow(self, ctx):
        """
        Check the slowmode for a channel
        """
        await ctx.send(
            f" The current slow mode in the channel is {ctx.channel.slowmode_delay} seconds"
        )


async def setup(bot):
    await bot.add_cog(LockAndSlow(bot))
