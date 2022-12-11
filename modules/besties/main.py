from wsgiref import validate
import discord
from discord.ext import commands, tasks
import re 
import asyncio
import logging

async def setup(bot):
    await bot.add_cog(Besties(bot))
    logging.info('Besties cog has loaded')


class Besties(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot.loop.create_task(self.connect_db())
        self.pending_besties = set()

    #def cog_unload(self):
    #    self.timed_handler.cancel()
    #    self.daily_task.cancel()
    #    # COMPLETELY CANCELS the task.
    async def connect_db(self):
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS besties (user1 integer, user2 integer)")
        await self.bot.db_conn.commit()
    
    async def get_besties(self, id):
        all_finds = set()
        finds = await self.bot.db_conn.execute("SELECT * FROM besties WHERE user1 = ? OR user2 = ?", (id,id))
        finds = await finds.fetchall()
        for x in finds:
            for y in x:
                if y != id:
                    all_finds.add(y)
        return all_finds
    
    async def add_bestie(self, id1, id2):
        await self.bot.db_conn.execute("INSERT INTO besties VALUES (?, ?)", (id1, id2))
        await self.bot.db_conn.commit()
    
    async def remove_bestie(self, id1, id2):
        await self.bot.db_conn.execute("DELETE FROM besties WHERE user1 = ? AND user2 = ?", (id1, id2))
        await self.bot.db_conn.commit()
    
    @commands.guild_only()
    @commands.command(name='bestie')
    async def bestie(self, ctx, member:discord.Member):
        if ctx.author is member:
            await ctx.reply("You cannot bestie yourself.")
            return
        if member.id in self.pending_besties:
            await ctx.reply('That user has a pending bestie request. Try again later!')
            return
        cur_besties = await self.get_besties(ctx.author.id)
        if len(cur_besties) == 10:
            await ctx.reply('You can only have 10 besties.')
            return
        if member.id in cur_besties:
            await ctx.reply("You are already besties with that user.")
            return

        def check(m):
            logging.info(f'CHECK: message author is {m.id}, waiting for {member.id}')
            return m.author.id == member.id and m.content.lower() in ['y', 'n']
        try:
            await ctx.reply(f'{member.mention}, {ctx.author.mention} would like to become besties with you. Send a \'Y\' if you would like this, or \'N\' if not.')
            self.pending_besties.add(member.id)
            message = await self.bot.wait_for('message', timeout=60.0, check=check)
        except asyncio.TimeoutError:
            await ctx.reply(f'{member.mention} did not make up their mind in time. Bestie request cancelled!')
            self.pending_besties.remove(member.id)
            return
        else:
            if message.content.lower() == 'y':
                await self.add_bestie(ctx.author.id, member.id)
                await message.reply(f'{member.mention} and {ctx.author.mention} are now besties!')
                self.pending_besties.remove(member.id)
                return
            elif message.content.lower() == 'n':
                await message.reply(f'{ctx.author.mention}, HEARTBREAK! {member.mention} declined the bestie request!')
                self.pending_besties.remove(member.id)
                return
    
    @commands.guild_only()
    @commands.command(name='unbestie')
    async def unbestie(self, ctx, member:discord.Member):
        if ctx.author is member:
            await ctx.reply("You cannot unbestie yourself.")
            return
        cur_besties = await self.get_besties(ctx.author.id)
        if member.id not in cur_besties:
            await ctx.reply("You are not besties with that user.")
            return
        await self.remove_bestie(ctx.author.id, member.id)
        await ctx.reply('Done. Best of luck with your future friendships!')

    @commands.guild_only()
    @commands.command(name='besties')
    async def besties(self, ctx, member:discord.Member=None):
        member = member or ctx.author
        besties = await self.get_besties(member.id)
        embed = discord.Embed(
            title = f'{member.display_name}\'s besties',
            color = discord.Colour.orange()
        )
        if not besties:
            embed.description = 'They don\'t have any :('
        else:
            embed.description = ""
            for b in besties:
                user = self.bot.get_user(b)
                if user:
                    user = user.mention
                else:
                    user = 'Unknown user'
                embed.description = embed.description + user + '\n'
        embed.set_footer(text=f'Requested by {str(ctx.author)}')
        embed.set_thumbnail(url=member.display_avatar.url)
        await ctx.reply(embed=embed)

