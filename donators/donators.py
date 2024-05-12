import discord
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
import asyncio
import re

from core import checks
from core.models import PermissionLevel
from core.paginator import EmbedPaginatorSession

class PerkButton(discord.ui.Button):
    def __init__(self, *, label, disabled, emoji = None):
        style = discord.ButtonStyle.gray if disabled else discord.ButtonStyle.success
        super().__init__(style=style, label=label, disabled=disabled, emoji=emoji, row=0)

    async def callback(self, interaction: discord.Interaction):
        return await super().callback(interaction)

class RedemptionView(discord.ui.View):
    def __init__(self, *, ctx: commands.Context, user_id: int, perks_unlocked: list[int]):
        super().__init__(timeout=180)
        self.context = ctx
        self.user_id = user_id
        self.add_buttons(perks_unlocked)
    
    def add_buttons(self, perks_unlocked: list[int]) -> None:
       for perk in (5, 10, 20, 30):
           disabled = perk not in perks_unlocked
           self.add_item(PerkButton(label=f"${perk}", disabled=disabled))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("That's not your buttons")
            return False

        return True

    async def on_timeout(self) -> None:
        return await super().on_timeout()

class Donators(commands.Cog):
    """
    Manage cash donator perks
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)
        self.check_expiry.start()
        self.channel_check.start()
        self.update_vcs.start()
        self.top10_roles.start()

    async def get_details(self, donator_id: int) -> dict | None:
        return await self.coll.find_one({"user_id": donator_id})
    
    async def add_donation(self, donator_id: int, amount: int, proof: str) -> None:
        await self.coll.update_one(
            {"user_id": donator_id},
            {
                "$inc": {"balance": amount, "total_donated": amount},
                "$push": {
                    "Donation": {
                        "Value": amount,
                        "Date": datetime.now(timezone.utc),
                        "Proof": proof,
                    }
                },
                "$setOnInsert": {
                    "expiry": "None",
                    "perk_name": "None",
                    "channel_id": "None"
                }
            },
            upsert=True,
        )
    
    async def remove_donation(self, donator_id: int, amount: int, proof: str) -> None:
        amount = -abs(amount)
        await self.coll.update_one(
            {"user_id": donator_id},
            {
                "$inc": {"balance": amount, "total_donated": amount},
                "$push": {
                    "Donation": {
                        "Value": amount,
                        "Date": datetime.now(timezone.utc),
                        "Proof": proof,
                    }
                },
            }
        )

    def add_donation_details(self, embed: discord.Embed, donation_info: dict) -> None:
        # Adds the details to the embed itself
        balance, total_donated, perk_level = donation_info["balance"], donation_info["total_donated"], donation_info["perk_name"]
        exp = None

        if (expiry := donation_info["expiry"]) != "None":
            timestamp = round(datetime.timestamp(expiry))
            exp = f"<t:{timestamp}:f>"
            
        embed.add_field(
            name="Total Donated:", value=f"${total_donated}", inline=True
        ).add_field(
            name="Balance:", value=f"${balance}", inline=True
        ).add_field(
            name="Perks Redeemed", value=perk_level, inline=True
        ).add_field(
            name="Expiry", value=exp, inline=True
        )

    async def confirm(
        self,
        ctx,
        member: discord.Member,
        balance,
        perk_value,
        perk_level,
        validity,
        totdonated,
        url,
    ):
        expiry = datetime.utcnow() + timedelta(days=validity)
        if expiry != "None":
            timestamp = round(datetime.timestamp(expiry))
            exp = f"<t:{timestamp}:f>"
        else:
            exp = "None"
        total = balance - perk_value
        await ctx.send(
            f"{member.mention}, Are you sure you want to redeem the `{perk_level}` perk for {validity} days? (yes/no)"
        )
        try:
            msg = await self.bot.wait_for(
                "message",
                timeout=30,
                check=lambda m: m.author == ctx.author
                and m.channel.id == ctx.channel.id,
            )
            if msg.content.lower() == "yes":
                if perk_value in (20, 30):
                    await ctx.send(
                        "You are eligible for a autoreact on ping. Do you want one? (yes/no)"
                    )
                    try:
                        msg = await self.bot.wait_for(
                            "message",
                            timeout=30,
                            check=lambda m: m.author == ctx.author
                            and m.channel.id == ctx.channel.id,
                        )
                        if msg.content.lower() == "yes":
                            await ctx.send(
                                "Please send ONLY the emoji you want to use. **Must be in this server**"
                            )
                            try:
                                msg = await self.bot.wait_for(
                                    "message",
                                    timeout=30,
                                    check=lambda m: m.author == ctx.author
                                    and m.channel.id == ctx.channel.id,
                                )
                                ar = {"user_id": member.id, "reaction": msg.content}
                                await self.bot.db.plugins.Autoreact.insert_one(ar)
                                await ctx.send(
                                    f"Added reaction {msg.content} for {member.mention}"
                                )
                            except asyncio.TimeoutError:
                                await ctx.send(
                                    f"{member.mention} has cancelled the perk redemption."
                                )
                                return False
                        elif msg.content.lower() == "no":
                            pass
                        else:
                            await ctx.send(
                                f"{member.mention} has cancelled the perk redemption."
                            )
                            return False
                    except asyncio.TimeoutError:
                        await ctx.send(
                            f"{member.mention} has cancelled the perk redemption."
                        )
                        return False
                await self.coll.update_one(
                    {"user_id": member.id},
                    {
                        "$set": {
                            "balance": total,
                            "perk_name": perk_level,
                            "expiry": expiry,
                        },
                        "$push": {
                            "Donation": {
                                "Value": -abs(perk_value),
                                "Date": datetime.utcnow(),
                                "Proof": url,
                            }
                        },
                    },
                )
                embed = discord.Embed(
                    title="**Perk Redeemed**",
                    description=f"{member.mention} has redeemed the {perk_level} perk.",
                    color=0x10EA64,
                )
                embed.add_field(
                    name="Total Donated:", value=f"${totdonated}", inline=True
                )
                embed.add_field(name="Balance:", value=f"${total}", inline=True)
                embed.add_field(
                    name="Perks Redeemed", value=f"{perk_level}", inline=True
                )
                embed.add_field(name="Expiry", value=exp, inline=True)
                await ctx.send(embed=embed)
                return True
            else:
                await ctx.send(f"{member.mention} has cancelled the perk redemption.")
                return False
        except asyncio.TimeoutError:
            await ctx.send(f"{member.mention} has cancelled the perk redemption.")
            return False

    async def resetmem(self, user):
        guild = self.bot.get_guild(645753561329696785)
        member = guild.get_member(user)
        if not member:
            await self.coll.update_one(
                {"user_id": user}, {"$set": {"perk_name": "None", "expiry": "None"}}
            )
            return True
        donator5 = guild.get_role(794300647137738762)
        donator10 = guild.get_role(794301192359378954)
        donator20 = guild.get_role(794301389769015316)
        donator30 = guild.get_role(794302939371929622)
        if donator5 in member.roles:
            await member.remove_roles(donator5)
        if donator10 in member.roles:
            await member.remove_roles(donator10)
        if donator20 in member.roles:
            await member.remove_roles(donator20)
        if donator30 in member.roles:
            await member.remove_roles(donator30)
        await self.coll.update_one(
            {"user_id": user}, {"$set": {"perk_name": "None", "expiry": "None"}}
        )
        await member.send("You cash donator perks have expired in `The Farm`. gg/dank")
        ar = await self.bot.db.plugins.Autoreact.find_one({"user_id": user})
        if ar:
            await self.bot.db.plugins.Autoreact.delete_one({"user_id": user})
        return True

    @commands.group(invoke_without_command=True)
    async def donator(self, ctx: commands.Context):
        """
        Donator commands.
        """
        return

    @donator.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def add(self, ctx: commands.Context, member: discord.Member, amount: int, proof):
        """
        Adds the donated value to the member.
        """
        await self.add_donation(member.id, amount, proof)
        donation_info = await self.get_details(member.id)
        
        embed = discord.Embed(
            title="**Amount added**",
            description=f"{member.mention} has had ${amount} added to their balance.",
            color=0x5865F2,
        )

        await self.add_donation_details(embed, donation_info)
        await ctx.reply(embed=embed)
        
        if self.channel_check.is_running():
            self.channel_check.restart()
        else:
            self.channel_check.start()

        if self.update_vcs.is_running():
            self.update_vcs.restart()
        else:
            self.update_vcs.start()

        if self.top10_roles.is_running():
            self.top10_roles.restart()
        else:
            self.top10_roles.start()

    @donator.command()
    @checks.has_permissions(PermissionLevel.ADMIN)
    async def remove(self, ctx: commands.Context, member: discord.Member, amount: int):
        """
        Removes the donated value from the member.
        """
        donation_info = await self.get_details(member.id)

        if donation_info is None:
            return await ctx.reply(f"{member.name} is not a donator yet and has no balance.")

        if donation_info["balance"] < amount:
            return await ctx.reply("How do you plan to remove more than they have?")
        
        url = ctx.message.jump_url
        await self.remove_donation(member.id, amount, url)

        embed = discord.Embed(
            title="**Amount removed**",
            description=f"{member.mention} has had ${amount} removed from their balance.",
            color=0x5865F2,
        )

        self.add_donation_details(embed)
        await ctx.reply(embed=embed)

    @donator.command(name="balance")
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def _balance(self, ctx: commands.Context, member: discord.Member):
        """
        Shows the balance of the member.
        """
        donation_info = await self.get_details(member.id)

        if donation_info is None:
            return await ctx.reply(f"{member.name} is not a donator yet and has no balance.")

        embed = discord.Embed(
            title="**Balance**",
            description=f"If you are looking for details, use `??donator details {member.id}`.",
            color=0x5865F2,
        )
        
        self.add_donation_details(embed, donation_info)
        await ctx.send(embed=embed)

    @donator.command()
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def details(self, ctx: commands.Context, member: discord.Member):
        """Shows details of each donation"""
        donation_info = await self.get_details(member.id)

        if donation_info is None:
            return await ctx.reply(f"{member.name} is not a donator yet and has no balance.")
        
        donations = donation_info["Donation"]

        chunks = [donations[i:i+10] for i in range(0, len(donations), 10)]
        embeds = []

        for batch in chunks:
            embed = discord.Embed(
                title=f"**{member.name}'s detailed donations**",
                description="",
                color=0x5865F2,
            )

            for entry in batch:
                date, value, proof = entry["Date"], entry["Value"], entry["Proof"]
                timestamp = round(datetime.timestamp(date))

                embed.description += f"<t:{timestamp}:f> - [${value}]({proof})\n"
            
            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()

    @donator.command()
    async def redeem(self, ctx: commands.Context):
        """
        Redeem perks from balance
        """
        donation_info = await self.get_details(ctx.author.id)
        if donation_info is None:
            return await ctx.reply("You are not a donator yet and have no balance.")

        if donation_info["perk_name"] != "None":
            return await ctx.reply("You have already redeemed a perk. Please wait for it to expire.")
        
        perks_unlocked = [p for p in (5, 10, 20, 30) if donation_info["balance"] >= p]
        
        redemption_embed = discord.Embed(title="**Balance**", colour=0x5865F2)
        self.add_donation_details(redemption_embed, donation_info)
        redemption_view = RedemptionView(ctx=ctx, user_id=ctx.author.id, perks_unlocked=perks_unlocked)

        await ctx.reply("Which perk level would you like to redeem?\nCheck out <#948755871167565824> for benefits of each tier", embed=redemption_embed, view=redemption_view)


    @donator.group(invoke_without_command=True, aliases=["lb"])
    @checks.has_permissions(PermissionLevel.MODERATOR)
    async def leaderboard(self, ctx: commands.Context):
        """
        Shows the donator leaderboard
        """

        balance_embed = discord.Embed(description="")
        balance_embed.set_author(name="Top users with the most balance")

        top10_embed = discord.Embed(description="")
        top10_embed.set_author(name="Top 10 donors in the past 30 days")

        top_1_embed = discord.Embed(description="")
        top_1_embed.set_author(name="Idk what this is lmao")

        session = EmbedPaginatorSession(ctx, balance_embed, top_1_embed, top10_embed)
        await session.run()

        return

    @leaderboard.command()
    async def total(self, ctx: commands.Context):
        """
        Shows the total donated leaderboard
        """
        top = await self.coll.find().sort("total_donated", -1).to_list(length=None)
        chunks = [top[i:i+10] for i in range(0, len(top), 10)]
        embeds = []
        previous_total, current_position = None, None

        for page_pos, batch in enumerate(chunks):
            embed = discord.Embed(title="**Top Donators**", description="", colour=0x10EA64)
            for pos, donation_information in enumerate(batch, start=1):
                user_id, total = donation_information["user_id"], donation_information["total_donated"]
                position = pos + page_pos * 10

                if total == previous_total:
                    position = current_position
                    
                if total != previous_total:
                    previous_total = total
                    current_position = position

                embed.description += f"{position}) <@{user_id}> ➜ ${total}\n"

            embeds.append(embed)

        session = EmbedPaginatorSession(ctx, *embeds)
        await session.run()

    @leaderboard.command()
    async def balance(self, ctx: commands.Context):
        """
        Shows the balance leaderboard
        """
        top = await self.coll.find().sort("balance", -1).to_list(length=None)

        embed = discord.Embed(title="**Top Balance**", description="", colour=0x10EA64)
        for pos, donation_information in enumerate(top, start=1):
            user_id, total = (
                donation_information["user_id"],
                donation_information["balance"],
            )

            embed.description += f"{pos}. <@{user_id}> ➜ ${total}\n"

        embed.set_footer(text="Page: 1")
        message = await ctx.send(embed=embed)
        await message.add_reaction("\U000025c0")
        await message.add_reaction("\U000025b6")

    @leaderboard.command()
    async def top10(self, ctx):
        """
        Shows the top 10 donators in the last month
        """
        s = ""
        top10 = await self.coll.aggregate(
            [
                {
                    "$set": {
                        "Donation30d": {
                            "$filter": {
                                "input": "$Donation",
                                "cond": {
                                    "$lt": [
                                        {
                                            "$dateDiff": {
                                                "startDate": "$$this.Date",
                                                "endDate": "$$NOW",
                                                "unit": "day",
                                            }
                                        },
                                        30,
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "sum30d": {
                            "$sum": {
                                "$filter": {
                                    "input": "$Donation30d.Value",
                                    "cond": {"$gt": ["$$this", 0]},
                                }
                            }
                        }
                    }
                },
                {"$sort": {"sum30d": -1}},
                {"$limit": 10},
            ]
        ).to_list(None)
        for i in top10:
            value = i["sum30d"]
            if value <= 0:
                continue
            user_id = i["user_id"]
            user = await self.bot.fetch_user(user_id)
            s += f"<@{user.id}> - ${value}\n"
        embed = discord.Embed(title="Top 10 Donators", description=s, colour=0x10EA64)
        await ctx.send(embed=embed)

    @leaderboard.command()
    async def top1(self, ctx):
        """
        Shows the top all time donator
        """
        s = ""
        top1 = await self.coll.aggregate(
            [
                {
                    "$set": {
                        "Donation90d": {
                            "$filter": {
                                "input": "$Donation",
                                "cond": {
                                    "$lt": [
                                        {
                                            "$dateDiff": {
                                                "startDate": "$$this.Date",
                                                "endDate": "$$NOW",
                                                "unit": "day",
                                            }
                                        },
                                        90,
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "sum90d": {
                            "$sum": {
                                "$filter": {
                                    "input": "$Donation90d.Value",
                                    "cond": {"$gt": ["$$this", 0]},
                                }
                            }
                        }
                    }
                },
                {"$sort": {"sum90d": -1}},
                {"$limit": 1},
            ]
        ).to_list(None)
        for i in top1:
            value = i["sum90d"]
            user_id = i["user_id"]
            user = await self.bot.fetch_user(user_id)
            s += f"<@{user.id}> - ${value}\n"
        embed = discord.Embed(title="Top 1 Donator", description=s, colour=0x10EA64)
        await ctx.send(embed=embed)

    @tasks.loop(hours=12)
    async def check_expiry(self):
        """
        Checks if the expiry time > current time.
        """
        try:
            fetchall = (
                await self.coll.find({"expiry": {"$ne": "None"}})
                .sort("expiry", 1)
                .to_list(10)
            )  # Top 10
            current_time = datetime.utcnow()
            for x in fetchall:
                if current_time >= x["expiry"]:
                    user = x["user_id"]
                    await self.resetmem(user)
        except Exception as e:
            print(e)

    @tasks.loop(hours=12)
    async def channel_check(self):
        """
        Get top 10 leaderboard
        """
        top10 = await self.coll.aggregate(
            [
                {
                    "$set": {
                        "Donation30d": {
                            "$filter": {
                                "input": "$Donation",
                                "cond": {
                                    "$lt": [
                                        {
                                            "$dateDiff": {
                                                "startDate": "$$this.Date",
                                                "endDate": "$$NOW",
                                                "unit": "day",
                                            }
                                        },
                                        30,
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "sum30d": {
                            "$sum": {
                                "$filter": {
                                    "input": "$Donation30d.Value",
                                    "cond": {"$gt": ["$$this", 0]},
                                }
                            }
                        }
                    }
                },
                {"$sort": {"sum30d": -1}},
                {"$limit": 10},
            ]
        ).to_list(None)
        havechannel = await self.coll.find({"channel_id": {"$ne": "None"}}).to_list(
            None
        )

        for i in top10:
            if i["sum30d"] > 0:
                user_id = i["user_id"]
                user = await self.bot.fetch_user(user_id)
                channel_id = i["channel_id"]
                if channel_id == "None":
                    guild = self.bot.get_guild(645753561329696785)
                    category = guild.get_channel(800961886824824832)
                    channel = await category.create_text_channel(
                        f"{user.name}", reason="Top 10 Leaderboard"
                    )
                    await self.coll.update_one(
                        {"user_id": user_id}, {"$set": {"channel_id": channel.id}}
                    )
                    overwrites = channel.overwrites_for(user)
                    (
                        overwrites.embed_links,
                        overwrites.attach_files,
                        overwrites.external_emojis,
                    ) = (True, True, True)
                    (
                        overwrites.send_messages,
                        overwrites.view_channel,
                        overwrites.manage_channels,
                    ) = (True, True, True)
                    (
                        overwrites.manage_messages,
                        overwrites.manage_permissions,
                        overwrites.mention_everyone,
                    ) = (True, False, False)
                    await channel.set_permissions(user, overwrite=overwrites)
                    await channel.send(
                        f"Welcome to your channel {user.mention}! Thanks for donating! \n You can use the `??au` "
                        f"command "
                        f"to add people to this channel!"
                    )
                else:
                    continue
            else:
                continue

        for y in havechannel:
            user_id = y["user_id"]
            if user_id in [x["user_id"] for x in top10] and [
                x["sum30d"] > 0 for x in top10
            ]:
                continue
            else:
                channel_id = y["channel_id"]
                guild = self.bot.get_guild(645753561329696785)
                channel = guild.get_channel(channel_id)
                user = await self.bot.fetch_user(user_id)
                await channel.send(
                    f"Your channel will be deleted in 24 hours since you’re no longer in the top 10 donators! Ignore "
                    f"if you alr got this warning! \n{user.mention}"
                )
                self.bot.loop.create_task(self.delete_channel(channel_id, user_id))

    async def delete_channel(self, channel_id, user_id):
        await asyncio.sleep(86400)
        top10 = await self.coll.aggregate(
            [
                {
                    "$set": {
                        "Donation30d": {
                            "$filter": {
                                "input": "$Donation",
                                "cond": {
                                    "$lt": [
                                        {
                                            "$dateDiff": {
                                                "startDate": "$$this.Date",
                                                "endDate": "$$NOW",
                                                "unit": "day",
                                            }
                                        },
                                        30,
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "sum30d": {
                            "$sum": {
                                "$filter": {
                                    "input": "$Donation30d.Value",
                                    "cond": {"$gt": ["$$this", 0]},
                                }
                            }
                        }
                    }
                },
                {"$sort": {"sum30d": -1}},
                {"$limit": 10},
            ]
        ).to_list(None)
        for z in top10:
            if user_id == z["user_id"] and z["sum30d"] > 0:
                return

        guild = self.bot.get_guild(645753561329696785)
        channel = guild.get_channel(channel_id)
        await channel.delete(
            reason="This channel has been deleted since they're no longer in the top 10 donators"
        )
        await self.coll.update_one(
            {"user_id": user_id}, {"$set": {"channel_id": "None"}}
        )

    @tasks.loop(hours=11)
    async def update_vcs(self):
        top3 = (
            await self.coll.find().sort("total_donated", -1).limit(3).to_list(length=3)
        )
        """Update vcs in a category"""
        guild = self.bot.get_guild(645753561329696785)
        top_vcs = [
            guild.get_channel(i)
            for i in (794480467561938955, 877672534890405958, 877672580272762921)
        ]
        for vc, entry in zip(top_vcs, top3):
            user_id, donated = entry["user_id"], entry["total_donated"]
            user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)

            if f"{user} (${donated})" == vc.name:
                continue

            await vc.edit(name=f"{user} (${donated})")

    @tasks.loop(hours=11)
    async def top10_roles(self):
        top10 = await self.coll.aggregate(
            [
                {
                    "$set": {
                        "Donation30d": {
                            "$filter": {
                                "input": "$Donation",
                                "cond": {
                                    "$lt": [
                                        {
                                            "$dateDiff": {
                                                "startDate": "$$this.Date",
                                                "endDate": "$$NOW",
                                                "unit": "day",
                                            }
                                        },
                                        30,
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "$set": {
                        "sum30d": {
                            "$sum": {
                                "$filter": {
                                    "input": "$Donation30d.Value",
                                    "cond": {"$gt": ["$$this", 0]},
                                }
                            }
                        }
                    }
                },
                {"$sort": {"sum30d": -1}},
                {"$limit": 10},
            ]
        ).to_list(None)
        guild = self.bot.get_guild(645753561329696785)
        toprole = guild.get_role(794392116079493121)
        for z in top10:
            user_id = z["user_id"]
            member = guild.get_member(user_id)
            if not member:
                continue
            if toprole in member.roles:
                continue
            else:
                await member.add_roles(toprole)
        for member in toprole.members:
            if member.id in [x["user_id"] for x in top10]:
                continue
            else:
                await member.remove_roles(toprole)


async def setup(bot):
    await bot.add_cog(Donators(bot))
