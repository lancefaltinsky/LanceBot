import discord
from discord.ext import commands, tasks
import logging

async def setup(bot):
    await bot.add_cog(Help(bot))
    logging.info('Help cog has loaded')

class Help(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx, command=None):
        if command:
            com = self.bot.get_command(name=command)
            if not com:
                await ctx.send('Command not found')
                return
            if com.hidden:
                await ctx.send('This command is not intended for your use')
                return
            if com.description == '':
                desc = 'No description'
            else:
                desc = com.description
            if not com.usage:
                usage = 'No usage help provided'
            else:
                usage = com.usage
            embed = discord.Embed(
                title=f'{self.bot.prefix}{com.name}',
                description=desc,
                color=discord.Colour.red()
            )
            embed.add_field(name='Usage', value=usage)
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title=f'{self.bot.name} help',
                description='Type +help command to get help on a specific command',
                color=discord.Colour.red()
            )
            for c in self.bot.cogs.keys():
                com_str = ''
                commands = []
                for com in self.bot.cogs[c].get_commands():
                    if not com.hidden:
                        commands.append(com.name)
                if len(commands) > 0:
                    com_str = ', '.join(commands)
                    embed.add_field(name=c, value=com_str, inline=False)
            embed.set_footer(text=f'My current prefix is {self.bot.prefix}')
            embed.set_thumbnail(url=self.bot.user.avatar)
            await ctx.send(embed=embed)
