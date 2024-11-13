from discord.ext import commands
from core import checks
from core.models import PermissionLevel

STAFF_ROLE_ID = 1231811207095128085

class StaffRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Click here", style=discord.ButtonStyle.green, custom_id="fight_farm_ban_battle_view")
    async def toggle_staff_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user._roles.has(STAFF_ROLE_ID):
            await interaction.user.remove_roles(discord.Object(id=STAFF_ROLE_ID))
            return await interaction.response.send_message("Removed the Staff role, you can now participate in the battles", ephemeral=True)

        await interaction.user.add_roles(discord.Object(id=STAFF_ROLE_ID))
        await interaction.response.send_message("Added the Staff role, you can now host battles", ephemeral=True)


class BanBattles(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._fight_farm = None
        # self.bot.add_view(message_id=)

    @property
    def fight_farm(self):
        # fight farm may not be cached when the cog is loaded, hence we create a
        # property to retreive it after all guilds has been cached
        if self._fight_farm is None:
            self._fight_farm = bot.get_guild(1231809717597372446)

        return self._fight_farm

    @commands.Cog.listener("on_member_join")
    async def give_staff_role(self, member: discord.Member):
        if member.guild.id != 1231809717597372446:
            return

        # if they're a Giveaway Manager in The Farm,
        # allow them to always have perms to see # staff-chat
        if self.bot.modmail_guild.get_member(member.id)._roles.has(855877108055015465):
            staff_chat = self.fight_farm.get_channel(1231810076319158292)
            await staff_chat.set_permissions(member, view_channel=True)

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
        ban_battle_channel = self.fight_farm.get_channel(1231809717597372449)

        invite = await ban_battle_channel.create_invite(max_age=5 * 60, max_uses=uses, reason="Hosting ban battle")
        await ctx.send(
            "# Welcome to Ban Battles!\n"
            "- During this event, everyone who joins the will be able to ban others in the server until only one person remains\n"
            "- The event is a free-for-all, meaning that everyone is allowed to ban others and can be banned by others in turn\n"
            "- The last person left in the server wins\n\n"
            f"Here's the invite link for the ban battle: {invite}\n"
            "-# (If it says it's an invalid invite, you missed the event!)"
        )

    @commands.command(hidden=True)
    async def send_staff_role_message(self, ctx: commands.Context):
        if ctx.author.id != 531317158530121738:
            return

        embed = discord.Embed(title="Staff role", description="Click the button to add/remove your staff role", colour=0x5865F2)

        await ctx.message.delete()
        message = await ctx.send(embed=embed, view=StaffRoleView())
        await ctx.send(f"Message id: {message.id}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BanBattles(bot))
