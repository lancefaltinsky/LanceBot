import discord
from discord.ext import commands, tasks
import random

async def setup(bot):
    await bot.add_cog(Statusrotation(bot))

class Statusrotation(commands.Cog):
    def __init__ (self, bot):
        with open('static/statuses.txt','r+', encoding='utf-8') as f:
            self.statuses = f.read().splitlines()
        self.bot = bot
        self.statupdate.start()
        print("Status rotation extension has loaded!")

    def cog_unload(self):
        self.statupdate.cancel()

    @tasks.loop(seconds=300.0)
    async def statupdate(self):
        if self.bot.is_closed() and not self.bot.isready():
            return
        game = random.choice(self.statuses)
        await self.bot.change_presence(activity=discord.Game(name=game))
