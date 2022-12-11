from discord.ext import commands, tasks
import discord
from difflib import get_close_matches
import sys
import traceback
import logging

async def setup(bot):
    await bot.add_cog(Errorhandler(bot))

class Errorhandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Errorhandler initialized")
    
    def hprint(self, text):
        logging.info(f'[Errorhandler]: {text}')

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandInvokeError):
            error = error.original
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(f'Sorry, but you used this command too recently and are on cooldown.\n'
                           f'You may use this command again in {round(error.retry_after)} seconds.')
            return

        # copypasted code from tag. pretty basic tho so i dont rly feel bad
        if isinstance(error, commands.CommandNotFound):
            cmd = ctx.invoked_with
            cmds = [cmd.name for cmd in self.bot.commands]
            matches = get_close_matches(cmd, cmds)
            if len(matches) > 0:
                match_str = '\n'.join(matches)
                await ctx.send(f'Command `"{cmd}"` not found, did you mean:\n{match_str}')
            else:
                await ctx.send(f'Command "{cmd}" not found, run +help to see all available commands')
            return

        if isinstance(error, commands.NSFWChannelRequired):
            await ctx.send(f'This command may only be used in NSFW channels!')
            return

        if isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(f'You may only use this message in private DM\'s with me!')
            return

        if isinstance(error,commands.NoPrivateMessage):
            await ctx.send('You can\'t use this command in private messages.')
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f'You are missing a required parameter for that command: `{error.param.name}`\n'
                           f'The proper usage for this command is `{ctx.command.usage}`')
            return

        if isinstance(error, commands.DisabledCommand):
            await ctx.send('This command is disabled.')
            return

        if isinstance(error, commands.NotOwner):
            await ctx.send('This command is only for the bot owner.')

        if isinstance(error, commands.MemberNotFound):
            await ctx.send(f'Sorry, I could not find that member (\"{error.argument}\"). Maybe they left the server or you spelt their name wrong.')
            return

        if isinstance(error, commands.ChannelNotFound):
            await ctx.send(f'Channel \"{error.argument}\" not found')
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send('You do not have the required permissions to do that.')
            return

        if isinstance(error, commands.MissingPermissions):
            await ctx.send('I do not have the required permissions to do that.')
            return

        if isinstance(error, commands.BadArgument):
            await ctx.send(f'I could not understand the input you gave me for this command. Please check your input.\n'
                       f'Error(s): `{error.args}`')
            return
        
        if isinstance(error, commands.CheckFailure):
            return
        else:
            etype = type(error)
            trace = error.__traceback__
            error = traceback.format_exception(etype, error, trace)
            logging.info(error)
            await ctx.reply(f"uh oh spaghetti-o! i got an error. maybe tell lance about this (only if he isn\'t going to flip his shit about something being broken tho):\nTraceback (if any):\n```{''.join(error)[:1500]}```")

