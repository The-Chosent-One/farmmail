from discord.ext import commands
from contextlib import redirect_stdout
import io
import traceback
import textwrap
import discord

class DonationTracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.coll = bot.plugin_db.get_partition(self)

    def cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')
    
    


async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))