from discord.ext import commands
from core import checks
from core.models import PermissionLevel

class BanBattles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(aliases=["bb", "banbattles"])
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def banbattle(self, ctx: commands.Context, uses: int = 0):
        """
        Creates an invite link for the Ban Battle server, which expries in 5 minutes.
        This command will send an explanation for how ban battles work, together with the invite link.
        
        You can specify a maximum number of people the invite will accept: ??bb 10
        You can leave it blank as well, and anyone can join within the 5 minutes (??bb)
        """

        await ctx.message.delete()
        ban_battle_channel = self.bot.get_guild(1231809717597372446).get_channel(1231809717597372449)
        
        invite = await ban_battle_channel.create_invite(max_age=5*60, max_uses=uses, reason="Hosting ban battle")
        await ctx.send(
            "# Welcome to Ban Battles!\n"
            "- During this event, everyone who joins the will be able to ban others in the server until only one person remains\n"
            "- The event is a free-for-all, meaning that everyone is allowed to ban others and can be banned by others in turn\n"
            "- The last person left in the server wins\n\n"
            f"Here's the invite link for the ban battle: {invite}"
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(BanBattles(bot))
