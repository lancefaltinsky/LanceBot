import discord
from discord.ext import commands, tasks
from datetime import datetime
from datetime import timedelta
from bs4 import BeautifulSoup
import configparser
import random
import logging
from pytz import timezone
import random

channel = channel_id_here

async def setup(bot):
    await bot.add_cog(Daily(bot))
    logging.info("Daily module loaded")

class Daily(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.daily_task.start()

    def hprint(self, text):
        logging.info(f"[Daily]: {text}")

    def cog_unload(self):
        self.daily_task.cancel()
        # COMPLETELY CANCELS the task.
    
    async def get_holidays_for_today(self):
        async with self.bot.aio_session.get("https://nationaltoday.com/what-is-today/") as page:
            page = await page.text()
            soup = BeautifulSoup(page, 'lxml')
            finds = [f.text.strip() for f in soup.find_all('h3', {'class':'holiday-title'})]
        holidays = '\n• '+'\n• '.join(finds)
        return holidays
  
    @tasks.loop(hours=24)
    async def daily_task(self):
        send_channel = self.bot.get_channel(channel)
        randoms = ["rise and shine gamers!", "good morning yall.", "good morning!", "wakey wakey eggs and bakey bitches!", "YOOOOOOOO good morning!!!", "yoo top of the morning", "time to wake the fuck up!"]
        greeting = random.choice(randoms)
        holidays = await self.get_holidays_for_today()
        uotd = random.choice(self.bot.get_guild(guild_id_here).members)
        await send_channel.send(f'{greeting} Today\'s holidays are: {holidays}\nToday\'s (random) member of the day is {uotd.mention}!')

    @daily_task.before_loop
    async def wait_until_12am(self):
        now = datetime.now(timezone('EST'))
        next_run = now.replace(hour=8, minute=0, second=0)

        if next_run < now:
            next_run += timedelta(days=1)
        await discord.utils.sleep_until(next_run)
    
    @commands.command(name='today')
    async def today(self, ctx):
        holidays = await self.get_holidays_for_today()
        await ctx.reply(f"Today is {datetime.now().strftime('%m/%d/%Y')}. Today\'s holidays: {holidays}")
