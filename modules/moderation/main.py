import discord
from discord.ext import commands
import discord
import logging
import configparser
import random
from typing import Union

async def setup(bot):
    await bot.add_cog(Moderation(bot))


class Moderation(commands.Cog):
    def __init__ (self, bot):
        self.bot = bot
        self.hprint("Moderation cog initialized")
        self.log_channel = 972719703678124112
        self.admin_channel = bot.get_channel(972719693628571658)
        self.bot.loop.create_task(self.connect_db())
    
    async def connect_db(self):
        await self.bot.db_conn.execute(
            "CREATE TABLE IF NOT EXISTS warns (snowflake integer, warner integer, reason text, warnid integer)")
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS prohibited_content (content text)")
        await self.bot.db_conn.commit()
        await self.bot.db_conn.execute('PRAGMA journal_mode=WAL')
        await self.bot.db_conn.commit()

    async def add_warn(self, id, warner, reason):
        embed = discord.Embed(
            title=f'⚠ You were warned in Server Name',
            color=discord.Colour.orange()
        )
        warner_user = self.bot.get_user(warner)
        target_user = self.bot.get_user(id)
        embed.add_field(name='Warned by',value=f'{warner_user.mention}',inline=False)
        embed.add_field(name='Reason',value=f'\"{reason}\"',inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar.url or self.bot.user.default_avatar.url)
        embed.set_footer(text='Remember, don\'t let this ruin your day: this is just a warn!')
        try:
            await target_user.send(embed=embed)
        except:
            embed.title = f'⚠ {str(target_user)} was warned'
            await self.bot.get_channel(764634697833512970).send(content=target_user.mention, embed=embed)
        await self.admin_channel.send(f'{target_user.mention} was warned for \"{reason}\"')
        warn_id = random.randint(10000, 100000)
        await self.bot.db_conn.execute("INSERT INTO warns VALUES (?,?,?,?)", (id, warner, reason, warn_id))
        await self.bot.db_conn.commit()

    def is_target(self, m):
        return m.author == self.target

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='clear', description='Clears x amount of message in chat overall, or from a specific user',
                      usage='+clear amount optional:user')
    async def clear(self, ctx, msg_count, target: discord.Member = None):
        if not msg_count:
            await ctx.send('Please enter how many messages need to be deleted')
            return
        try:
            msg_count = int(msg_count) + 1
        except:
            await ctx.send('Invalid message count')
            return
        if target:
            self.target = target
            deleted = await ctx.channel.purge(limit=msg_count, check=self.is_target)
        else:
            deleted = await ctx.channel.purge(limit=msg_count)
        msg = f'Done! {len(deleted)} messages deleted.'
        if len(deleted) < msg_count:
            msg = f'Done! {len(deleted)} messages deleted.\n' \
                  f'Some could not be deleted as they are not in the internal cache.'
        await ctx.send(msg, delete_after=5)

    async def get_warns(self, id):
        cur = await self.bot.db_conn.execute("SELECT * FROM warns WHERE snowflake = ?", (id,))
        cur = await cur.fetchall()
        return cur

    async def remove_warn(self, mem_id, warn_id):
        if warn_id == 'all':
            await self.bot.db_conn.execute("DELETE FROM warns WHERE snowflake = ?", (mem_id,))
            await self.bot.db_conn.commit()
            return
        await self.bot.db_conn.execute("DELETE FROM warns WHERE snowflake = ? AND warnid = ?", (mem_id,warn_id,))
        await self.bot.db_conn.commit()

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='warn')
    async def warn(self, ctx, mem: discord.Member, *, reason):
        await self.add_warn(mem.id, ctx.author.id, reason)
        await ctx.message.delete()

    @commands.command(name='warns')
    async def warns(self,ctx,mem:discord.Member=None):
        if not mem:
            mem = ctx.author
        warns = await self.get_warns(mem.id)
        embed = discord.Embed(
            title=f'Warns for @{mem.name}',
            color=discord.Colour.purple()
        )
        if not warns:
            await ctx.send('You do not have any warns. Congrats! :)')
            return
        for w in warns:
            embed.add_field(name=f'Warned by @{self.bot.get_user(w[1])}, warn ID: {w[3]}',value=f'Reason: \"{w[2]}\"',inline=False)
        embed.set_thumbnail(url=self.bot.user.avatar.url or self.bot.user.default_avatar.url)
        await ctx.send(embed=embed)

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='removewarn')
    async def removewarn(self,ctx,mem:discord.Member,warn_id):
        if warn_id != 'all':
            await self.remove_warn(mem.id, warn_id)
            await ctx.send('Warn has been removed')
            return
        await self.remove_warn(mem.id, 'all')
        await ctx.send('All warns have been removed')

    def hprint(self, text):
        logging.info(f'[Moderation]: {text}')

    async def do_log_event(self, user, event, description, _from="", _to=""):
        embed = discord.Embed()
        embed.set_footer(text=f'User ID: {user.id}')
        embed.set_thumbnail(url=user.display_avatar.url)
        if event == "msg_delete":
            embed.title = f'A message from {str(user)} was deleted'
            embed.description = f'\"{description}\"'
            embed.color = discord.Colour.red()
        elif event == "msg_edit":
            embed.title = f'{str(user)} edited a message'
            embed.color = discord.Colour.orange()
            embed.add_field(name='From', value = _from, inline=False)
            embed.add_field(name='To', value = _to, inline=False)
        elif event == "voice_join":
            embed.title = f'{str(user)} joined a voice channel'
            embed.description = description
            embed.color = discord.Colour.green()
        elif event == "voice_leave":
            embed.title = f'{str(user)} left a voice channel'
            embed.description = description
            embed.color = discord.Colour.red()
        elif event == "voice_switch":
            embed.title = f'{str(user)} switched voice channels'
            embed.add_field(name='From', value = _from, inline=False)
            embed.add_field(name='To', value = _to, inline=False)
            embed.color = discord.Colour.orange()
        elif event == "webcam_on":
            embed.title = f'{str(user)} turned their webcam on'
            embed.description = description
            embed.color = discord.Colour.green()
        elif event == "webcam_off":
            embed.title = f'{str(user)} turned their webcam off'
            embed.description = description
            embed.color = discord.Colour.red()
        elif event == "stream_on":
            embed.title = f'{str(user)} turned their screenshare on'
            embed.description = description
            embed.color = discord.Colour.green()
        elif event == "stream_off":
            embed.title = f'{str(user)} turned their screenshare off'
            embed.description = description
            embed.color = discord.Colour.red()
        elif event == "mute":
            embed.title = f'{str(user)} muted/deafened themselves'
            embed.description = description
            embed.color = discord.Colour.red()
        elif event == "unmute":
            embed.title = f'{str(user)} unmuted/deafened themselves'
            embed.description = description
            embed.color = discord.Colour.green()
        embed.add_field(name='User', value = user.mention, inline= False)
        webhook = await self.bot.setup_utility_webhook(self.bot.get_channel(self.log_channel))
        if webhook:
            await webhook.send(embed=embed, username=f"{str(user)}\'s logged event", avatar_url = user.display_avatar.url)
    
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @commands.command(name='ban', description = 'Ban a user', hidden=True) 
    async def _ban(self, ctx, user_id:str, reason='No reason given'):
        user = discord.Object(id=user_id)
        await ctx.guild.ban(user, reason = reason)
        await ctx.message.add_reaction('✅')

    @commands.Cog.listener()
    async def on_message_delete(self, msg):
        if msg.author is msg.guild.me or msg.channel.id == self.log_channel:
            return
        await self.do_log_event(msg.author, "msg_delete", msg.clean_content or "-Blank message content-")
    
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
        if before.author is before.guild.me or before.channel.id == self.log_channel:
            return
        await self.do_log_event(before.author, "msg_edit", "", before.clean_content or "-Blank message content-", after.clean_content or "-Blank message content-")
    
    @commands.Cog.listener()
    async def on_voice_state_update(self, mem, before, after):
        if mem is mem.guild.me:
            return
        if not before.channel and after.channel:
            await self.do_log_event(mem, "voice_join", after.channel.mention)
        elif before.channel and not after.channel:
            await self.do_log_event(mem, "voice_leave", before.channel.mention)
        elif before.channel and after.channel and before.channel != after.channel:
            await self.do_log_event(mem, "voice_switch", "", before.channel.mention, after.channel.mention)
        elif not before.self_video and after.self_video:
            await self.do_log_event(mem, "webcam_on", after.channel.mention)
        elif before.self_video and not after.self_video:
            await self.do_log_event(mem, "webcam_off", after.channel.mention)
        elif not before.self_stream and after.self_stream:
            await self.do_log_event(mem, "stream_on", after.channel.mention)
        elif before.self_stream and not after.self_stream:
            await self.do_log_event(mem, "stream_off", after.channel.mention)
        elif not before.self_mute and after.self_mute:
            await self.do_log_event(mem, "mute", after.channel.mention)
        elif before.self_mute and not after.self_mute:
            await self.do_log_event(mem, "unmute", after.channel.mention)

    @commands.Cog.listener()
    async def on_member_remove(self, mem):
        embed = discord.Embed(
            title=f'❌ {str(mem)} left the server',
            description='farewell i guess',
            color=discord.Colour.red()
        )
        embed.set_thumbnail(url=mem.avatar.url or mem.default_avatar.url)
        embed.set_footer(text=mem.id)
        await self.logchannel.send(embed=embed)