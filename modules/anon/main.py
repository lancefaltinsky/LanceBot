from discord.ext import commands, tasks
import discord
import aiosqlite
import aiohttp
import logging


async def setup(bot):
    await bot.add_cog(Anon(bot))
    logging.info('Anon cog has loaded')

class Anon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.connect_db())
        self.anon_channel = self.bot.get_channel(anon_channel_id_here)

    async def connect_db(self):
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS anon_users (snowflake integer, fakename text, is_banned integer, is_active integer)")
        await self.bot.db_conn.commit()

    async def get_or_create_user_name(self, id:int, ctx):
        cur = await self.bot.db_conn.execute("SELECT fakename FROM anon_users WHERE snowflake = ? AND is_active = 1", (id,))
        cur = await cur.fetchone()
        if cur:
            return cur[0]
        if not cur:
            name_api = 'https://randomuser.me/api/'
            async with self.bot.aio_session.get(name_api) as response:
                name_json = await response.json()
                name = name_json['results'][0]['name']
                fakename = name['first'] + ' ' + name['last']
            await self.bot.db_conn.execute("INSERT INTO anon_users VALUES (?,?,?,?)", (id, fakename, 0, 1))
            await self.bot.db_conn.commit()
            await ctx.send(f'Welcome! Your fake name has been generated and is `{fakename}`\n'
                           f'As this name is supposed to be completely anonymous and random, we do not grant the ability to change it.\n'
                           f'Your identity will only ever be revealed to admins if we need to do so for moderation. Nobody apart from the admins and in these cases will ever know who you are.\n'
                           f'Remember to have fun and follow all server rules- they still apply!\n'
                           f'**If you need a new anon name at any time, just do `+refreshanon`!**')
            return fakename

    async def deprecate_anon(self, id):
        await self.bot.db_conn.execute("UPDATE anon_users SET is_active = 0 WHERE snowflake = ?", (id,))
        await self.bot.db_conn.commit()

    @commands.dm_only()
    @commands.cooldown(1, 3, type=commands.BucketType.user)
    @commands.command(name='anonsay', description='Uses anon talk', usage='+anonsay hello world')
    async def a(self, ctx, *, msg):
        fakename = await self.get_or_create_user_name(ctx.author.id, ctx)
        webhooks = await self.anon_channel.webhooks()
        cur_webhook = None
        if ctx.message.attachments:
            await ctx.send('This system does not currently support attachments. Sorry.\n'
                           'If you need to send an image, send an image URL as your message.')
            return
        for w in webhooks:
            if w.name == 'Anon webhook':
                cur_webhook = w
        if not cur_webhook:
            cur_webhook = await self.anon_channel.create_webhook(name='Anon webhook', avatar=None, reason=None)
        await cur_webhook.send(msg, username=fakename, avatar_url='https://i.imgur.com/DEZ978Y.png')
        await ctx.message.add_reaction('✅')

    @commands.dm_only()
    @commands.cooldown(1,86400, type=commands.BucketType.user)
    @commands.command(name='refreshanon',description='Refreshes your anon name')
    async def refreshanon(self, ctx):
        cur = await self.bot.db_conn.execute("SELECT * FROM anon_users WHERE snowflake = ?", (ctx.author.id,))
        cur = await cur.fetchone()
        if not cur:
            await ctx.send('You do not have a currently active anon account')
            return
        await self.deprecate_anon(ctx.author.id)
        await ctx.send('OK! I have disabled your current anon ID. Please use the anon command at any time to create a new one!')

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='anonwhois')
    async def anonwhois(self, ctx, *, search):
        cur = await self.bot.db_conn.execute("SELECT fakename, snowflake FROM anon_users WHERE fakename = ? AND is_active = 1", (search,))
        cur = await cur.fetchone()
        if not cur:
            await ctx.send('Could not find any anon anon_users with that name')
            return
        mem = self.bot.get_user(cur[1])
        await mem.send(f'{mem.mention}, an admin used a command to reveal your anonymous identity. You likely broke a rule.')
        await ctx.send(f'{search} is {str(mem)}')