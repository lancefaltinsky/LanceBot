import discord
from discord.ext import commands
import discord
import logging
import configparser

async def setup(bot):
    await bot.add_cog(Modulehandler(bot))

config = configparser.ConfigParser()
config.read('config.ini')
default_prefix = str(config['lancebot']['default_prefix'])

class Modulehandler(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.hprint("Module handler initialized")
        self.bot.loop.create_task(self.load_modules_from_config())
        
    def hprint(self, text):
        logging.info(f'[ModuleHandler]: {text}')

    async def load_modules_from_config(self):
        modules = str(config['modules']['enabled_modules'])
        if ',' in modules:
            modules = modules.split(',')
        else:
            modules = [modules]
        for m in modules:
            m = m.strip().lower()
            await self.load_module(None, m)

    async def load_module(self, channel, module):
        try:
            await self.bot.load_extension(f'modules.{module}.main')
            if channel:
                await channel.send(f'Module {module} loaded successfully')
                self.hprint(f'Module {module} loaded successfully')
        except Exception as e:
            self.hprint(f'Error loading module {module}: {e}')
            if channel:
                await channel.send(f"Extension error:\n```{str(e)}```")
            raise e

    async def unload_module(self, channel, module):
        try:
            await self.bot.unload_extension(f'modules.{module}.main')
            if channel:
                await channel.send(f'Module {module} unloaded successfully')
                self.hprint(f'Module {module} unloaded successfully')
        except Exception as e:
            self.hprint(f'Error unloading module {module}: {e}')
            if channel:
                await channel.send(f"Extension error:\n```{str(e)}```")
            raise e

    @commands.is_owner()
    @commands.command(name='loadmodule', description = 'Loads a module', hidden=True) 
    async def loadmodule(self,ctx, extname):
        await self.load_module(ctx.channel, extname)

    @commands.is_owner()
    @commands.command(name='unloadmodule', description='Unloads a module', hidden=True) 
    async def unloadmodule(self,ctx, extname):
        await self.unload_module(ctx.channel, extname)

    @commands.is_owner()
    @commands.command(name='reloadmodule', description='Reloads a module', hidden=True) 
    async def reloadmodule(self, ctx, extname):
        await self.unload_module(ctx.channel, extname)
        await self.load_module(ctx.channel, extname)