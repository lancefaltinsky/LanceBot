import discord
from discord import utils
from discord.ext import commands, tasks
import logging
from datetime import datetime, timezone
import pytz
from bs4 import BeautifulSoup
import async_google_trans_new 

async def setup(bot):
    await bot.add_cog(Utility(bot))

class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Utility cog initialized")
        self.translator = async_google_trans_new.AsyncTranslator()

    def hprint(self, text):
        logging.info(f'[Utility]: {text}')

    @commands.is_owner()
    @commands.command() 
    async def synccommands(self, ctx, here="no"):
        if here.lower() == 'guild':
            await ctx.bot.tree.sync(guild=ctx.guild)
        else:
            await ctx.bot.tree.sync()
        await ctx.reply("Synced.")
    
    @commands.command(name='nztime')
    async def nztime(self, ctx):
        tz = pytz.timezone('Pacific/Auckland')
        nz_now = datetime.now(tz)
        nz_now = nz_now.strftime('%A, %B %d %I:%M %p')
        await ctx.reply(f'It is currently {nz_now} in New Zealand')
    
    @commands.is_owner()
    @commands.command(name='sql', hidden=True)
    async def _sql(self, ctx, *, sql):
        try:
            cursor = await self.bot.db_conn.execute(sql)
            cursor = await cursor.fetchall()
            await self.bot.db_conn.commit()
        except Exception as e:
            await ctx.reply(f"Error: {e}")
            return
        await ctx.send(cursor)

    
    @commands.bot_has_permissions(move_members=True)
    @commands.command(name='vcmove', description='Moves everyone in a VC to another VC')
    async def _vcmove(self, ctx, vc1:discord.VoiceChannel, vc2:discord.VoiceChannel=None):
        if not vc2:
            if ctx.author.voice:
                vc2 = vc1
                vc1 = ctx.author.voice.channel
        for member in vc1.members:
            await member.move_to(vc2)
        await ctx.reply(f"Moved everyone from {vc1.name} to {vc2.name}")

    @commands.command(name='uptime', description='Tells you how long the bot has been online for')
    async def _uptime(self, ctx):
        delta_uptime = datetime.utcnow() - self.bot.launch_time
        hours, remainder = divmod(int(delta_uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        await ctx.send(f"Bot has been online for {days} days, {hours} hours, {minutes} minutes, {seconds} seconds")

    @commands.command(name='membercount', description='Tells you how many members are in the server')
    async def _membercount(self, ctx):
        bots = 0
        humans = 0
        for m in ctx.guild.members:
            if m.bot:
                bots += 1
            else:
                humans += 1
        await ctx.reply(f"There are {humans} humans, {bots} bots currently in this server!")
    
    @commands.command(name='latency',description='Gets the bot\'s current latency',usage=f'+latency')
    async def _latency(self, ctx):
        await ctx.send(f'Latency was {self.bot.latency}')
    
    @commands.command(name='user',description='Gets info on a user',usage=f'+user OR +user user')
    async def _user(self,ctx,mem:discord.Member=None):
        if not mem:
            mem = ctx.author
        embed = discord.Embed(
            title = f'Info about @{str(mem)}',
            color = discord.Colour.green()
        )
        embed.add_field(name='Joined server at',value=mem.joined_at.strftime('%m/%d/%y %I:%M %p'),inline=False)
        embed.add_field(name='User ID',value=mem.id,inline=False)
        if not mem.premium_since:
            prem_status = 'Not boosting the server :('
        else:
            prem_status = mem.premium_since.strftime('%m/%d/%y %I:%M %p')
        embed.add_field(name='Premium since',value=prem_status,inline=False)
        embed.add_field(name='Top role',value=mem.top_role.name,inline=False)
        embed.add_field(name='Real name',value=mem.name,inline=False)
        embed.add_field(name='Account created on',value=mem.created_at.strftime('%m/%d/%y %I:%M %p'),inline=False)
        embed.set_thumbnail(url=mem.avatar.url or mem.default_avatar.url)
        embed.set_footer(text=f'Info requested by @{str(ctx.author)}')
        await ctx.send(embed=embed)
    
    @commands.command(name='server',description='Gets info on the server',usage='+server')
    async def _server(self,ctx):
        guild = ctx.guild
        embed = discord.Embed(
            title = f'Info about {guild.name}',
            color = discord.Colour.green()
        )
        embed.add_field(name='Owner',value=str(guild.owner), inline=False)
        embed.add_field(name='Created on',value=guild.created_at.strftime('%m/%d/%Y'),inline=False)
        embed.add_field(name='Description',value=guild.description,inline=False)
        embed.add_field(name='Max members',value=guild.max_members,inline=False)
        embed.add_field(name='Number of channels',value=len(guild.channels),inline=False)
        embed.add_field(name='Number of channel categories',value=len(guild.categories),inline=False)
        embed.add_field(name='Number of humans',value=sum([not m.bot for m in guild.members]),inline=False)
        embed.add_field(name='Number of bots',value=sum([m.bot for m in guild.members]),inline=False)
        embed.add_field(name='Number of roles',value=len(guild.roles),inline=False)
        embed.set_thumbnail(url=guild.icon.url)
        await ctx.send(embed=embed)
    
    def scrape_gas_prices(self, html, data):
        soup = BeautifulSoup(html, 'lxml')
        sorted_prices = []
        listings = soup.find_all('div', {'class':'GenericStationListItem-module__stationListItem___3Jmn4'})
        for l in listings:
            brand = l.find('h3', {'class':'header__header3___1b1oq header__header___1zII0 header__midnight___1tdCQ header__snug___lRSNK StationDisplay-module__stationNameHeader___1A2q8'}).find('a').text
            price = l.find('span', {'class':'text__xl___2MXGo'}).text
            address_parts = l.find('div', {'class':'StationDisplay-module__address___2_c7v'}).strings
            address = ' '.join(address_parts)
            sorted_prices.append((price, brand, address))
        disp_city = data[1].title().replace('-', ' ').strip()
        disp_state = data[0].title().replace('-', ' ').strip()
        return sorted_prices, disp_city, disp_state

    @commands.command(name='gasprices', description='Gets the lowest gas prices in your area', usage='+gasprices state, city')
    async def _gasprices(self, ctx, *, data):
        data = data.split(',')
        if len(data) < 2:
            await ctx.send('Please input a city and state')
            return
        new_data = []
        for d in data:
            new_data.append(d.strip().replace(' ', '-').lower())
        data = new_data
        logging.info(data)
        async with self.bot.aio_session.get(f'https://www.gasbuddy.com/gasprices/{data[0]}/{data[1]}') as resp:
            text = await resp.text()
            sorted_prices, disp_city, disp_state = await self.bot.loop.run_in_executor(None, self.scrape_gas_prices, text, data)
            if not sorted_prices:
                await ctx.reply("Sorry, I couldn\'t find any gas prices. Check your input and spelling.")
                return
            embed = discord.Embed(
                title = f'⛽ Lowest gas prices near {disp_city}, {disp_state}',
                color = discord.Colour.orange()
            )
            if len(sorted_prices) > 5:
                sorted_prices = sorted_prices[:5]
            for s in sorted_prices:
                embed.add_field(name = s[0], value = f'{s[1]}, {s[2]}', inline = False)
            await ctx.reply(embed=embed)
    
    @commands.cooldown(1, 30, type=commands.BucketType.user)
    @commands.command(name='cleanup', description='Cleans up the last 30 messages with bot commands and attempted bot commands/typos')
    async def cleanup(self, ctx):
        def is_bot_or_bot_command(m):
            return m.content.startswith(self.bot.prefix)

        deleted = await ctx.channel.purge(limit=30, check=is_bot_or_bot_command)
        await ctx.send(f"{ctx.author.mention} Done! {len(deleted)} messages removed.",delete_after=5)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        if reaction.emoji == '✅':
            for s in self.secrets:
                if s.message.id == reaction.message.id:
                    if user.id not in s.revealers:
                        s.add_revealer(user.id)
                        try:
                            await user.send(f'The secret was: ||{s.content}||')
                        except:
                            pass
        if reaction.emoji == '🌐' and len(reaction.message.reactions) == 1:
            message = reaction.message.clean_content
            translated_msg = await self.translator.translate(message, 'en')
            if message == translated_msg:
                return
            logging.info(translated_msg)
            embed = discord.Embed(
                title='Message translation requested',
                color = discord.Colour.orange()
            )
            embed.add_field(name='From', value = message, inline=False)
            embed.add_field(name='To', value  = translated_msg, inline=False)
            embed.add_field(name='Requested by', value=user.mention, inline=False)
            embed.set_thumbnail(url='https://i.imgur.com/pTsczqj.png')
            embed.set_footer(text='React to a message with 🌐 to translate it!')
            await reaction.message.reply(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.content.isnumeric():
            if int(msg.content) < 100000:
                return
            steam_id = (1 << 56 | 1 << 52 | 1 << 32 | int(msg.content))
            api = f'https://steamcommunity.com/actions/ajaxresolveusers?steamids={steam_id}'
            async with self.bot.aio_session.get(api) as response:
                user_json = await response.json()
                if not user_json:
                    return
                link = f'http://steamcommunity.com/profiles/{steam_id}'
                reply = await msg.reply(f'Looks like that\'s a Steam invite code. Here\'s a quick profile link to that user: \n{link}')

#await ctx.bot.tree.sync()
