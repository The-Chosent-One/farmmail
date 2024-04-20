from typing import Any
import discord
from discord.ext import commands
from motor import motor_asyncio


class CurrencyHandler:
    def __init__(
        self, bot: commands.Bot, collection: motor_asyncio.AsyncIOMotorCollection
    ) -> None:
        self.bot = bot
        self.collection: motor_asyncio.AsyncIOMotorCollection = collection

    async def _get_field(self, target: discord.Member, field: str) -> Any:
        res = await self.collection.find_one(
            {"user_id": target.id, field: {"$exists": True}}
        )

        return None if res is None else res.get(field)

    async def _modify_field(
        self,
        modification: str,
        target: discord.Member,
        field: str,
        value: Any,
        *,
        upsert: bool = False
    ) -> Any:
        res = await self.collection.find_one_and_update(
            {"user_id": target.id},
            {modification: {field: value}},
            upsert=upsert,
            return_document=True,
        )

        return None if res is None else res.get(field)

    async def get_cash(self, target: discord.Member) -> int:
        ret = await self._get_field(target, "cash")
        if ret is None:
            return 0

        return ret

    async def update_cash(self, target: discord.Member, cash: int) -> int:
        return await self._modify_field("$inc", target, "cash", cash, upsert=True)

    async def set_cash(self, target: discord.Member, cash: int) -> int:
        return await self._modify_field("$set", target, "cash", cash, upsert=True)

    async def get_next_income_time(self, target: discord.Member) -> int | None:
        return await self._get_field(target, "next_income_time")

    async def update_income_time(
        self, target: discord.Member, next_income_time: int
    ) -> None:
        await self._modify_field(
            "$set", target, "next_income_time", next_income_time, upsert=True
        )
