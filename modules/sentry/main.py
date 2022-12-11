import discord
from discord.ext import commands, tasks
import logging
import random
import datetime
import asyncio
import urllib.parse
import re
import arrow
import whois
import os
from datetime import datetime 
async def setup(bot):
    await bot.add_cog(Sentry(bot))
    logging.info('Sentry cog has loaded')


class Sentry(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.url_regex = r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+"
    
    def domain_parse(self, url):
        url = urllib.parse.urlparse(url).hostname
        if not url:
            return None
        url = url.replace('www.', '')
        return url
    
    def get_registered_date(self, domain):
        try:
            return whois.whois(domain)
        except:
            return datetime.now()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.id == message.guild.me:
            return
        links = re.findall(self.url_regex, message.content.lower())
        domains = set()
        if links:
            for l in links:
                l = self.domain_parse(l)
                domains.add(l)
            for l in domains:
                reg_date = await self.bot.loop.run_in_executor(None, self.get_registered_date, l)
                if (datetime.now() - reg_date).total_seconds() < 2592000:
                    embed = discord.Embed(
                        title = 'POSSIBLE SCAM! Please use caution when visiting this website!',
                        description = f'This website/domain is extremely new. If this website claims it is a free nitro giveaway, or that it is from any reputable source, it is more than likely a scam.\n\n'\
                        'Use extreme caution. Do not enter your account details for anything anywhere on this website (pages on it may be faked to look like they are from a reputable company such as Steam or Discord), do not download or run anything '\
                        'from it, and don\'t visit it at all if you don\'t need to.\n\nIf you have questions or concerns feel free to ask Lance.',
                        color = discord.Colour.orange()
                    )
                    embed.set_thumbnail(url = 'https://i.imgur.com/AeFMBvS.png')
                    await message.reply(embed=embed)
        

