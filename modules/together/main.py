import discord
from discord.ext import commands, tasks
import logging
import random
import datetime
import asyncio

async def setup(bot):
    await bot.add_cog(Together(bot))
    logging.info('Together cog has loaded')


class Together(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.scheduled_event = None
        self.guild = 972705503702552646
        self.bot.loop.create_task(self.event_check())
    
    async def event_check(self):
        guild = self.bot.get_guild(self.guild)
        mem_ct = 0
        active_vcs = []
        for v in guild.voice_channels:
            if v.members:
                mem_ct += sum([not v.bot for v in v.members])
                active_vcs.append(v)
        if not mem_ct:
            if self.scheduled_event:
                await self.scheduled_event.delete()
                self.scheduled_event = None
            return
        if mem_ct == 1:
            event_name = "1 member is in a VC!"
        else:
            event_name = f"{mem_ct} members are in VC!"
        if not self.scheduled_event:
            self.scheduled_event = await guild.create_scheduled_event(name = event_name, description = "Now is a good time to hang out!", start_time = discord.utils.utcnow() + datetime.timedelta(seconds=5), entity_type = discord.EntityType.voice, channel = random.choice(active_vcs))
            await self.scheduled_event.start()
        else:
            await self.scheduled_event.edit(name = event_name, channel = random.choice(active_vcs))

    @commands.Cog.listener()
    async def on_voice_state_update(self, mem, before, after):
        if not before.channel and after.channel:
            await self.event_check()
        elif before.channel and not after.channel:
            await self.event_check()