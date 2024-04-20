import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel
from datetime import datetime


class Carl(commands.Cog):
    """
    Some commands
    """

    def __init__(self, bot):
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    @commands.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def addtrigger(
        self,
        ctx,
        trigger: str,
        title: str,
        description: str,
        color: discord.Color,
        allowed_roles: commands.Greedy[discord.Role] = None,
        channels: commands.Greedy[discord.TextChannel] = None,
    ):
        """
        Add a trigger to send a message
        """
        if allowed_roles is None:
            allowed_roles = "None"
        else:
            allowed_roles = [r.id for r in allowed_roles]
        if channels is None:
            channels = "None"
        else:
            chaid = [c.id for c in channels]
            channels = chaid

        check = await self.coll.find_one({"trigger": trigger})
        if check:
            await ctx.send("Trigger already exists")
        else:
            await self.coll.insert_one(
                {
                    "trigger": trigger,
                    "title": title,
                    "description": description,
                    "color": color.value,
                    "allowed_roles": allowed_roles,
                    "channel": channels,
                }
            )
            await ctx.send("Added trigger")

    @commands.command(alias=["deltrigger"])
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def deletetrigger(self, ctx, trigger: str):
        """
        Delete a trigger that sends a message
        """
        check = await self.coll.find_one({"trigger": trigger})
        if check:
            await self.coll.delete_one(check)
            await ctx.send("Deleted trigger")
        else:
            await ctx.send("Trigger does not exist")

    @commands.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def trigger(self, ctx, trigger: str = None):
        """
        View a trigger and its set permissions
        """
        c = ""
        r = ""
        t = ""
        if trigger is None:
            fetchall = self.coll.find({})
            async for x in fetchall:
                trigger = x["trigger"]
                t += f"{trigger} \n"
            embed = discord.Embed(title="All triggers", description=t, color=0x00FF00)
            await ctx.send(embed=embed)
        else:
            find = await self.coll.find_one({"trigger": trigger})
            if find:
                description = find["description"]
                title = find["title"]
                channel = find["channel"]
                allowed_roles = find["allowed_roles"]
                embed = discord.Embed(title=title, description=description)
                if channel == "None":
                    c = "None"
                else:
                    for chamention in channel:
                        chamen = self.bot.get_channel(chamention)
                        c += f"{chamen.mention}, "
                if allowed_roles == "None":
                    r = "None"
                else:
                    for roleid in allowed_roles:
                        rolename = ctx.guild.get_role(roleid)
                        r += f"{rolename.name}, "
                if channel == "None" and allowed_roles == "None":
                    await ctx.send("This trigger is allowed everywhere.", embed=embed)
                if channel == "None" and allowed_roles != "None":
                    await ctx.send(
                        f"This trigger is allowed in all channels but only for these roles: \n {r}",
                        embed=embed,
                    )
                if channel != "None" and allowed_roles == "None":
                    await ctx.send(
                        f"This trigger is allowed in the channels: \n {c} for everyone.",
                        embed=embed,
                    )
                if channel != "None" and allowed_roles != "None":
                    await ctx.send(
                        f"This is only allowed in the channels \n {c} \n for who have one of the roles: \n {r}",
                        embed=embed,
                    )
            else:
                await ctx.send(
                    "Trigger does not exist, try `??trigger` to see available triggers"
                )

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.content.startswith("??"):
            return
        check = await self.coll.find_one({"trigger": message.content.lower()})
        if not check:
            return
        else:
            channel = check["channel"]
            allowed_roles = check["allowed_roles"]
            color = check["color"]
            title = check["title"]
            description = check["description"]
            if channel == "None" and allowed_roles == "None":
                embed = discord.Embed(title=title, description=description, color=color)
                return await message.channel.send(embed=embed)
            if channel == "None" and allowed_roles != "None":
                if any(r.id in allowed_roles for r in message.author.roles):
                    embed = discord.Embed(
                        title=title, description=description, color=color
                    )
                    return await message.channel.send(embed=embed)
            if channel != "None" and allowed_roles == "None":
                if message.channel.id in channel:
                    embed = discord.Embed(
                        title=title, description=description, color=color
                    )
                    return await message.channel.send(embed=embed)
            if channel != "None" and allowed_roles != "None":
                if (
                    any(r.id in allowed_roles for r in message.author.roles)
                    and message.channel.id in channel
                ):
                    embed = discord.Embed(
                        title=title, description=description, color=color
                    )
                    return await message.channel.send(embed=embed)

    @commands.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def embed(
        self, channel: discord.TextChannel, color: discord.Color, title, description
    ):
        """
        Send an embed in a channel
        """
        embed = discord.Embed(title=title, description=description, color=color)
        await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Carl(bot))
