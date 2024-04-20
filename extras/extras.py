import asyncio
import re
from datetime import timedelta
from pathlib import Path

import discord
import random
from core import checks
from core.models import PermissionLevel
from discord.ext import commands

time_units = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days", "w": "weeks"}

this_file_directory = Path(__file__).parent.resolve()
other_file = this_file_directory / "scammer.txt"

with open(other_file, "r+") as file:
    scammer = [scammer.strip().lower() for scammer in file.readlines()]


class Extras(commands.Cog):
    """
    Extra commands
    """

    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def _error(msg):
        return discord.Embed(description="** " + msg + " **", color=discord.Color.red())

    @staticmethod
    def to_seconds(s):
        return int(
            timedelta(
                **{
                    time_units.get(m.group("unit").lower(), "seconds"): int(
                        m.group("val")
                    )
                    for m in re.finditer(
                        r"(?P<val>\d+)(?P<unit>[smhdw]?)", s, flags=re.I
                    )
                }
            ).total_seconds()
        )

    @commands.Cog.listener("on_message")
    async def deleteall(self, message: discord.Message):
        if message.channel.id == 714533815829397506:
            await message.delete()

    @commands.Cog.listener("on_message")
    async def scammeralert(self, message: discord.Message):
        if not message.guild:
            return
        role = message.guild.get_role(824549659988197386)
        if message.author.bot:
            return
        if role in message.author.roles:
            if any(word in message.content.lower() for word in scammer):
                if message.mentions:
                    embed = discord.Embed(
                        title=f":warning: {message.author} is a scammer  :warning: ",
                        description="Hey, thought you should know the user you are engaging in a deal with is a **scammer** and has unpaid dues.",
                        color=0xFF0000,
                    )
                    embed.set_footer(text="- The Farm")
                    await message.channel.send(embed=embed)
        else:
            members = [m.name for m in message.mentions if role in m.roles]
            if members:
                if any(word in message.content.lower() for word in scammer):
                    if len(members) > 1:
                        embed = discord.Embed(
                            title=f":warning:  {', '.join(members)} are scammers  :warning: ",
                            description="Hey, thought you should know the user you are engaging in a deal with is a **scammer** and has unpaid dues. Proceed with caution",
                            color=0xFF0000,
                        )
                        embed.set_footer(text="- The Farm")
                        await message.channel.send(embed=embed)
                    elif len(members) == 1:
                        embed = discord.Embed(
                            title=f":warning:  {' '.join(members)} is a scammer  :warning: ",
                            description="Hey, thought you should know the user you are engaging in a deal with is a **scammer** and has unpaid dues. Proceed with caution",
                            color=0xFF0000,
                        )
                        embed.set_footer(text="- The Farm")
                        await message.channel.send(embed=embed)

    @commands.command()
    @commands.has_any_role(
        790290355631292467,
        855877108055015465,
        723035638357819432,
        814004142796046408,
        682698693472026749,
        658770981816500234,
        663162896158556212,
        658770586540965911,
    )
    async def inrole(self, ctx, role1: discord.Role, role2: discord.Role):
        """
        Get the unque members in 2 roles
        """
        first = role1.members
        second = role2.members
        firstlen = len(role1.members)
        secondlen = len(role2.members)
        unique = len(list(set(first + second)))
        await ctx.send(
            embed=discord.Embed(
                title="Here is the requested information!",
                colour=discord.Colour.green(),
                description=f"**Users in {role1}**: {firstlen} \n**Users in {role2}**: {secondlen} \n **unique in {role1} and {role2}**: {unique}",
            )
        )

    @commands.command()
    @checks.thread_only()
    async def unmute(self, ctx):
        """
        Unmute a user in a thread
        """
        member = ctx.guild.get_member(ctx.thread.id)

        role = discord.utils.get(member.guild.roles, name="Muted")
        if role in member.roles:
            await member.remove_roles(
                role, reason=f"Unmute requested by {str(ctx.author.id)}"
            )
            await ctx.channel.send("Unmuted")
        else:
            await ctx.channel.send("They arent muted")

    @commands.command()
    @commands.has_any_role(
        790290355631292467,
        855877108055015465,
        723035638357819432,
        814004142796046408,
        682698693472026749,
        658770981816500234,
        663162896158556212,
        658770586540965911,
    )
    async def whois(self, ctx, member: discord.Member = None):
        """
        Get information about a user
        """
        if member is None:
            member = ctx.message.author

        roles = [role for role in member.roles]
        embed = discord.Embed(
            colour=discord.Colour.green(), timestamp=ctx.message.created_at
        )
        embed.set_author(name=member.name, icon_url=member.avatar)
        embed.set_thumbnail(url=member.avatar)
        embed.set_footer(text=f"Requested by {ctx.author}")
        embed.add_field(
            name="Created Account On:",
            value=member.created_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"),
            inline=True,
        )
        embed.add_field(
            name="Joined Server On:",
            value=member.joined_at.strftime("%a, %#d %B %Y, %I:%M %p UTC"),
            inline=True,
        )
        embed.add_field(name="​", value="​", inline=False)
        embed.add_field(name="ID:", value=member.id, inline=True)
        embed.add_field(name="Display Name:", value=member.display_name, inline=True)
        embed.add_field(name="​", value="​", inline=False)
        embed.add_field(
            name="Roles:", value="".join([role.mention for role in roles]), inline=True
        )
        await ctx.send(embed=embed)

    @commands.command()
    async def timer(self, ctx, seconds):
        """
        Set a timer for a certain amount of time
        """
        try:
            text = seconds
            seconds = sum(
                int(num)
                * {"h": 60 * 60, "m": 60, "s": 1, " ": 1}[weight if weight else "s"]
                for num, weight in re.findall(r"(\d+)\s?([msh])?", text)
            )

            if not 4 < seconds < 21600:
                await ctx.message.reply(
                    "Please keep the time between 5 seconds to 6 hours"
                )
                raise BaseException

            message = await ctx.send(f"Timer: {seconds}")

            while True:
                seconds -= 5
                if seconds < 0:
                    await message.edit(content="Ended!")
                    return await ctx.message.reply(
                        f"{ctx.author.mention}, Your countdown has ended!"
                    )
                await message.edit(content=f"Timer: {seconds}")
                await asyncio.sleep(5)
        except ValueError:
            await ctx.message.reply("You must enter a number!")

    @commands.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def raw(self, ctx, msg: discord.Message):
        """
        Get the raw description of an embed
        """
        if not msg.embeds:
            return await ctx.send(
                embed=discord.Embed(
                    title="Please provide the message ID of an embedded message."
                )
            )

        await ctx.send(f"``` {msg.embeds[0].description} ```")

    @commands.command()
    @checks.thread_only()
    async def id(self, ctx):
        """Returns the Recipient's ID"""
        await ctx.send(ctx.thread.id)

    @commands.Cog.listener("on_presence_update")
    async def ggdank(self, before, after):
        if str(before.activity) == str(after.activity):
            return

        guild = self.bot.get_guild(645753561329696785)
        role = guild.get_role(916271809333166101)
        if role is None:
            return

        if after not in guild.members:
            return

        regex = re.compile(r"\b(discord.gg|\.gg|gg)/(dank)\b")
        if regex.search(str(after.activity)):
            if role not in after.roles:
                await after.add_roles(role)
        else:
            if role in after.roles:
                await after.remove_roles(role)


    @commands.command()
    @checks.thread_only()
    async def special(self, ctx):
        """
        Give the user the special role
        """
        member = ctx.guild.get_member(ctx.thread.id)

        role = discord.utils.get(
            member.guild.roles, name="▪ ⟶ ∽ ✰ ★ I'M SPECIAL ★ ✰ ∼ ⟵ ▪"
        )
        if role in member.roles:
            await member.remove_roles(
                role, reason=f"Special role removed, requested by {str(ctx.author.id)}"
            )
            await ctx.channel.send("The Special Role has been removed.")
        else:
            await member.add_roles(
                role, reason=f"Special role added, requested by {str(ctx.author.id)}"
            )
            await ctx.channel.send("The Special Role has been added.")

    @commands.command()
    @checks.thread_only()
    async def helpme(self, ctx):
        """
        Add chat mods to the thread and ping them
        """
        role = ctx.guild.get_role(814004142796046408)
        members = role.members
        members = [
            member for member in members if not member.status == discord.Status.offline
        ]
        members = random.sample(members, 1)
        channel = ctx.channel
        overwrites = channel.overwrites_for(role)
        overwrites.view_channel, overwrites.send_messages = True, True
        if channel.overwrites_for(role) == overwrites:
            return await ctx.send(f"{members[0].mention}")
        await channel.set_permissions(role, overwrite=overwrites)
        await ctx.send(f"{members[0].mention}")

    @commands.command()
    @checks.thread_only()
    async def helpme2(self, ctx):
        """
        Add chat mods to the thread but dont ping them
        """
        role = ctx.guild.get_role(814004142796046408)
        channel = ctx.channel
        overwrites = channel.overwrites_for(role)
        overwrites.view_channel, overwrites.send_messages = True, True
        if channel.overwrites_for(role) == overwrites:
            return await ctx.send(f"Already added to the channel.")
        await channel.set_permissions(role, overwrite=overwrites)
        await ctx.send(f"Added to the channel")

    @commands.command()
    @checks.thread_only()
    async def pms(self, ctx):
        """
        Add partner managers to the thread
        """
        role = ctx.guild.get_role(790290355631292467)
        channel = ctx.channel
        overwrites = channel.overwrites_for(role)
        overwrites.view_channel, overwrites.send_messages = True, True
        if channel.overwrites_for(role) == overwrites:
            return await ctx.send(f"Already added to the channel.")
        await channel.set_permissions(role, overwrite=overwrites)
        await ctx.send(f"Added to the channel")

    @commands.command()
    @commands.has_permissions(manage_channels=True)
    async def au(self, ctx, member: discord.Member):
        """
        Add a user to the channel
        """
        overwrites = ctx.channel.overwrites_for(member)
        overwrites.read_messages = True
        await ctx.channel.set_permissions(member, overwrite=overwrites)
        await ctx.channel.send(f"Added {member.mention}")


async def setup(bot):
    await bot.add_cog(Extras(bot))
