import asyncio
import re
import motor.motor_asyncio
from typing import Optional

import discord
from discord.ext import commands

LEADER_REGEX = re.compile(r"led.+<@!?(\d{17,19})>", flags=re.I)
SCOUTER_REGEX = re.compile(r"scout.+<@!?(\d{17,19})>", flags=re.I)
AMOUNT_REGEX = re.compile(r"[1-9]\d{0,2}(?:,\d{3})*")

# leaderboard stuff
class HeistDropDown(discord.ui.Select):
    def __init__(self, *, coll: motor.motor_asyncio.AsyncIOMotorCollection):
        options = [
            discord.SelectOption(label="Most led heists", emoji="💰"),
            discord.SelectOption(label="Most scouted heists", emoji="👀"),
        ]
        self.coll = coll

        super().__init__(
            placeholder="Choose a heist statistic to view",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        choice = self.values[0]

        embed = (message := interaction.message).embeds[0]
        embed.clear_fields()

        amount_field, count_field, field_name = {
            "Most led heists": ("led_amount", "led_count", "Top 5 most led heists!"),
            "Most scouted heists": (
                "scouted_amount",
                "scouted_count",
                "Top 5 most scouted heists!",
            ),
        }[choice]

        field_value = ""
        position = 1
        async for entry in self.coll.find(sort=[(amount_field, -1)], limit=5):
            leader, amount, count = (
                entry["user_id"],
                entry[amount_field],
                entry[count_field],
            )
            field_value += f"**{position}.** <@{leader}> — `⏣ {amount:,}` — {count:,}\n"
            position += 1

        embed.add_field(name=field_name, value=field_value)

        await message.edit(embed=embed)
        await interaction.response.defer()


class HeistView(discord.ui.View):
    def __init__(
        self,
        *,
        invoker: discord.Member,
        coll: motor.motor_asyncio.AsyncIOMotorCollection,
    ):
        super().__init__(timeout=30)
        self.invoker = invoker

        self.add_item(HeistDropDown(coll=coll))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.invoker:
            await interaction.response.send_message(
                "Hey, that's not yours to touch!", ephemeral=True
            )
            return False
        return True


# the actual cog
class HeistTracker(commands.Cog):
    """
    Heist statistics for heist leaders and scouts.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    def get_id(self, person: str, content: str) -> Optional[int]:
        _person_to_regex = {"leader": LEADER_REGEX, "scouter": SCOUTER_REGEX}
        regex = _person_to_regex[person]

        match = regex.search(content)

        if match is None:
            return None

        return int(match.group(1))

    def get_amount(self, content: str) -> Optional[int]:
        matches = AMOUNT_REGEX.findall(content)

        if matches != []:
            # we need to do this as the regex pattern matches multiple times for the discord ids.
            # minimum length it should be is 9, since it should be at least 1,000,000
            valid_matches = [*filter(lambda n: len(n) >= 9, matches)]

            # amount is missing
            if valid_matches == []:
                return None

            return int(valid_matches[0].replace(",", ""))

        return None

    async def update_db(self, leader_id: int, scouter_id: int, amount: int) -> None:
        # updates database with values using motor

        leader_info = await self.coll.find_one({"user_id": leader_id})
        if leader_info is None:
            await self.coll.insert_one(
                {
                    "user_id": leader_id,
                    "led_maximum": amount,
                    "led_amount": amount,
                    "led_count": 1,
                    "scouted_maximum": 0,
                    "scouted_amount": 0,
                    "scouted_count": 0,
                }
            )
        else:
            await self.coll.update_one(
                {"user_id": leader_id},
                {
                    "$set": {
                        "led_maximum": max(leader_info["led_maximum"], amount),
                        "led_amount": leader_info["led_amount"] + amount,
                        "led_count": leader_info["led_count"] + 1,
                    }
                },
            )

        scouter_info = await self.coll.find_one({"user_id": scouter_id})
        if scouter_info is None:
            await self.coll.insert_one(
                {
                    "user_id": scouter_id,
                    "led_maximum": 0,
                    "led_amount": 0,
                    "led_count": 0,
                    "scouted_maximum": amount,
                    "scouted_amount": amount,
                    "scouted_count": 1,
                }
            )
        else:
            await self.coll.update_one(
                {"user_id": leader_id},
                {
                    "$set": {
                        "scouted_maximum": max(leader_info["scouted_maximum"], amount),
                        "scouted_amount": leader_info["scouted_amount"] + amount,
                        "scouted_count": leader_info["scouted_count"] + 1,
                    }
                },
            )

    @commands.Cog.listener("on_message")
    async def recv_heist_msg(self, message: discord.Message):
        # trophy room
        if message.channel.id != 669866611313999882:
            return

        # we do this just in case the bot auto-deletes the heist message
        # if there's sensitive words in the message
        await asyncio.sleep(5)
        try:
            await message.channel.fetch_message(message.id)
        except discord.NotFound:
            # if the message has been deleted, ignore
            return

        content = message.content

        leader_id = self.get_id("leader", content)
        scouter_id = self.get_id("scouter", content)

        # either one of the ids are missing
        if not all((leader_id, scouter_id)):
            return

        amount = self.get_amount(content)

        if amount is None:
            return

        await self.update_db(leader_id, scouter_id, amount)

    @commands.group(
        aliases=["hs", "heiststatistics", "heiststat"], invoke_without_command=True
    )
    @commands.has_any_role(
        682698693472026749,
        658770981816500234,
        663162896158556212,
        658770586540965911,
        814004142796046408,
        855877108055015465,
        723035638357819432,
    )
    async def heiststats(self, ctx: commands.Context, user: discord.Member = None):
        """
        Heist statistics for heist leaders and scouts.
        """
        target = user or ctx.author
        user_id = target.id

        res = await self.coll.find_one({"user_id": user_id})

        if res is None:
            return await ctx.send(
                f"{target} does not have any unfriendly heist statistics"
            )

        embed = discord.Embed(
            title=f"{target}'s unfriendly heist statistics!", colour=0x303135
        )

        embed.description = (
            f"Number of heists led: **{res['led_count']:,}**\n"
            f"Total amount led: **⏣ {res['led_amount']:,}**\n"
            f"Largest amount led in one heist: **⏣ {res['led_maximum']:,}**\n"
            "\n"
            f"Number of heists scouted: **{res['scouted_count']:,}**\n"
            f"Total amount scouted: **⏣ {res['scouted_amount']:,}**\n"
            f"Largest amount scouted in one heist: **⏣ {res['scouted_maximum']:,}**\n"
        )

        await ctx.send(embed=embed)

    @heiststats.command(aliases=["lb"])
    async def leaderboard(self, ctx: commands.Context):
        """
        Leaderboard for heist leaders and scouts.
        """
        embed = discord.Embed(title="Leaderboard for heist statistics", colour=0x303135)

        all_heists = await self.coll.find(
            projection={"_id": False, "led_amount": True, "led_count": True}
        ).to_list(None)
        total_heist_amount = sum(e["led_amount"] for e in all_heists)
        total_heist_count = sum(e["led_count"] for e in all_heists)

        max_heist_info = await self.coll.find_one(sort=[("led_maximum", -1)])
        max_amount = max_heist_info["led_maximum"]

        embed.description = (
            "Go ahead, pick something!\n\n"
            f"Total amount heisted in The Farm: **⏣ {total_heist_amount:,}**\n"
            f"Number of heists done in The Farm: **{total_heist_count:,}**\n"
            f"Highest heist led in The Farm: **⏣ {max_amount:,}**"
        )

        heist_view = HeistView(invoker=ctx.author, coll=self.coll)

        message = await ctx.send(embed=embed, view=heist_view)

        await heist_view.wait()

        # disables the dropdown after 30 seconds
        heist_view.children[0].disabled = True
        await message.edit(view=heist_view)


async def setup(bot: commands.Bot):
    await bot.add_cog(HeistTracker(bot))
