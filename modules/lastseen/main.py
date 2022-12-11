import discord
from discord import utils
from discord.ext import commands, tasks
import asyncio
import aiosqlite
import arrow

async def setup(bot):
    await bot.add_cog(Lastseen(bot))

class Lastseen(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("Lastseen extension has loaded!")
        self.bot.loop.create_task(self.connect_db())

    async def connect_db(self):
        await self.bot.db_conn.execute(
            "CREATE TABLE IF NOT EXISTS lastseen_users (snowflake integer, lastseen text)")
        await self.bot.db_conn.commit()

    async def get_last_seen(self, authorid):
        cur = await self.bot.db_conn.execute("SELECT lastseen FROM lastseen_users WHERE snowflake=?", (authorid,))
        cur = await cur.fetchone()
        if not cur:
            return False
        return cur[0]

    async def update_ls(self, authorid):
        cur = await self.bot.db_conn.execute("SELECT EXISTS(SELECT 1 FROM lastseen_users WHERE snowflake=?)", (authorid,))
        cur = await cur.fetchone()
        now = str(arrow.utcnow().to('EST').format('MM/DD/YYYY'))
        if cur[0] == 0:
            await self.bot.db_conn.execute("INSERT into lastseen_users VALUES (?,?)", (authorid, now))
        else:
            await self.bot.db_conn.execute("UPDATE lastseen_users SET lastseen = ? WHERE snowflake = ?", (now, authorid))
        await self.bot.db_conn.commit()


    @commands.command(name='lastseen')
    async def lastseen(self, ctx, mem:discord.Member):
        ls = await self.get_last_seen(mem.id)
        if not ls:
            await ctx.reply('Could not determine when this user was last seen; they have not been active since the system was implemented.')
            return
        try:
            ls = arrow.get(ls, "MM/DD/YYYY")
        except:
            await ctx.reply(f'{mem.mention} was last seen on {ls}')
            return
        await ctx.reply(f'{mem.mention} was last seen on {ls.format("MM/DD/YYYY")}')

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.guild:
            await self.update_ls(msg.author.id)

    @commands.Cog.listener()
    async def on_member_join(self, mem):
        await self.update_ls(mem.id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, mem, b, a):
        if not b.channel and a.channel:
            await self.update_ls(mem.id)

    @commands.Cog.listener()
    async def on_typing(self, chan, user, when):
        if chan.type is discord.ChannelType.text:
            await self.update_ls(user.id)