import discord
from discord.ext import commands, tasks
import asyncio
import aiosqlite
import configparser
import datetime
import logging
import re
import random

async def setup(bot):
    await bot.add_cog(Levelling(bot))
    logging.info('Levelling system cog has loaded')


config = configparser.ConfigParser()
config.read('config.ini')
exclusions = config['levelling']['exclusions'].split(',')
alertchannel = int(config['levelling']['alertchannel'])
score_per_message = int(config['levelling']['messagescore'])
score_per_vc_minute = int(config['levelling']['vcminscore'])
booster_mult = int(config['levelling']['boostermult'])
sleep_channel = int(config['levelling']['sleepchannel'])


class Levelling(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.exclusions = exclusions
        self.alertchannel = self.bot.get_channel(alertchannel)
        self.bot.loop.create_task(self.connect_db())
        self.active_vc_members = []
        self.msgtimes = {}
        self.boostermult = booster_mult
        self.guildid = 972705503702552646
        self.sleep_channel = self.bot.get_channel(sleep_channel)
        self.emojire = '<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>'
        self.is_loading = True
        self.xbox360 = False

    async def connect_db(self):
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS user_vc_times (snowflake integer, vctime integer)")
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS inventories (snowflake integer, itemid text, used integer)")
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS items (itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text)")
        await self.bot.db_conn.commit()
        curs = await self.bot.db_conn.execute("SELECT * FROM levels")
        curs = await curs.fetchall()
        self.levelsinfo = {}
        for i in curs:
            self.levelsinfo[i[0]] = i[1]
        guild = self.bot.get_guild(self.guildid)
        for i in guild.voice_channels:
            # if  i is afk, return
            # oooor maybe we can get by, who knows
            for m in i.members:
                self.active_vc_members.append(m.id)
        self.vc_point_update.start()
        self.point_decay.start()

    async def check_user_vctime(self, id):
        vctime = await self.bot.db_conn.execute("SELECT vctime FROM user_vc_times WHERE snowflake=?", (id,))
        vctime = await vctime.fetchone()
        if not vctime:
            vctime = 0
            await self.bot.db_conn.execute("INSERT into user_vc_times VALUES (?,?)", (id, 0))
            await self.bot.db_conn.commit()
        else:
            vctime = vctime[0]
        return vctime

    async def create_or_update_vctime_tracker(self, id):
        vctime = await self.check_user_vctime(id)
        await self.bot.db_conn.execute("UPDATE user_vc_times SET vctime = ? WHERE snowflake = ?", (vctime + 1, id))
        await self.bot.db_conn.commit()

    @commands.guild_only()
    @commands.command(name='vctime', description='Displays how much total time you have spent in any VC')
    async def vctime(self, ctx, target:discord.Member=None):
        target = target or ctx.author
        vctime = int(await self.check_user_vctime(target.id))
        intervals = (
            ('weeks', 10080),  # 60 * 60 * 24 * 7
            ('days', 1440),    # 60 * 60 * 24
            ('hours', 60),    # 60 * 60
            ('minutes', 1)
        )
        # credit to top answer on
        # https://stackoverflow.com/questions/4048651/python-function-to-convert-seconds-into-minutes-hours-and-days
        human_time = []
        for name, count in intervals:
            value = vctime // count
            if value:
                vctime -= value * count
                if value == 1:
                    name = name.rstrip('s')
                human_time.append("{} {}".format(value, name))
        finished_human_time =  ', '.join(human_time[:2])
        if not finished_human_time:
            finished_human_time = '1 minute'
        await ctx.reply(f'{target.name}\'s total time spent in any VC is: \n' + finished_human_time)

    async def create_user_if_not_in_db(self, id):
        cur = await self.bot.db_conn.execute("SELECT EXISTS(SELECT 1 FROM level_users WHERE snowflake=?)", (id,))
        cur = await cur.fetchone()
        if cur[0] == 0:
            await self.bot.db_conn.execute("INSERT into level_users VALUES (?,?,?)", (id, 0, 0))
            guild = self.bot.get_guild(self.guildid)
            print("id ", id)
            mem = guild.get_member(id)
            await self.add_and_check_score(mem, guild, 0)
            await self.bot.db_conn.commit()

    async def get_user_score(self, id):
        curscore = await self.bot.db_conn.execute("SELECT score FROM level_users WHERE snowflake = ?", (id,))
        curscore = await curscore.fetchone()
        if not curscore:
            await self.create_user_if_not_in_db(id)
            curscore = await self.bot.db_conn.execute("SELECT score FROM level_users WHERE snowflake = ?", (id,))
            curscore = await curscore.fetchone()
        return curscore[0]

    async def modify_user_score(self, id, num):
        curscore = await self.get_user_score(id)
        newscore = num + curscore
        if newscore < 0:
            newscore = 0
        await self.bot.db_conn.execute("UPDATE level_users SET score = ? WHERE snowflake = ?", (round(newscore), id))
        await self.bot.db_conn.commit()

    async def add_and_check_score(self, mem, guild, reward):
        if not mem:
            return
        if mem.premium_since and reward > 0:
            reward = reward * booster_mult
        await self.modify_user_score(mem.id, reward)
        score = await self.get_user_score(mem.id)
        for x in self.levelsinfo.keys():
                role = guild.get_role(self.levelsinfo[x])
                if score >= x:
                    if role not in mem.roles:
                        await mem.add_roles(role)
                        name = mem.nick or mem.name
                        embed = discord.Embed(
                            title="⬆️ Level up!",
                            description=f'{mem.mention} has earned the `{role.name}` role!',
                            color=discord.Colour.red()
                        )
                        embed.set_footer(text=f"Total points: {score}")
                        embed.set_thumbnail(url=mem.avatar)
                        await self.alertchannel.send(embed=embed,content=f'Congratulations, {mem.mention}!')
                elif score < x:
                    if role in mem.roles:
                        print(f'{str(mem)} should not have the role ({str(role)}), removing')
                        await mem.remove_roles(role)

    async def get_leaderboard(self, admin_ids):
        print(admin_ids)
        query = f"SELECT * FROM level_users WHERE snowflake NOT in ({','.join(['?']*len(admin_ids))}) ORDER BY score DESC LIMIT 5"
        print(query)
        cur = await self.bot.db_conn.execute(query, admin_ids)
        cur = await cur.fetchall()
        print(cur)
        return cur

    # also create user in db if not already
    @commands.Cog.listener()
    async def on_message(self, msg):
        if not msg.author.bot and msg.channel.id not in self.exclusions and msg.guild:
            if msg.author.id in self.msgtimes.keys():
                now = datetime.datetime.now()
                secsdiff = now - self.msgtimes[msg.author.id]
                secsdiff = secsdiff.total_seconds()
                emojiamt = len(re.findall(self.emojire, msg.content))
                if secsdiff > 5 and emojiamt <= 1:
                    await self.create_user_if_not_in_db(msg.author.id)
                    await self.add_and_check_score(msg.author, msg.guild, score_per_message + random.randint(-2, 2))
            self.msgtimes[msg.author.id] = datetime.datetime.now()

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='addpoints', hidden=True)
    async def addpoints(self, ctx, mem: discord.Member, pts:int):
        if not mem or not pts:
            await ctx.send('Incomplete arguments')
            return
        if type(pts) != int:
            await ctx.send('Invalid points argument')
            return
        await self.create_user_if_not_in_db(mem.id)
        await self.add_and_check_score(mem, ctx.guild, pts)
        await mem.send(f'{mem.mention}, your levelling points have been manually adjusted by an admin.\n'
                       f'Adjustment value: {pts}')
        await ctx.message.add_reaction('✅')

    @commands.guild_only()
    @commands.command(name='levels',
                      description='Tells you your current level score and lists all the available levels',
                      usage='+levels',aliases=['points','score'])
    async def levels(self, ctx, arg=None):
        showall = False
        if arg and arg.lower() == 'all':
            showall = True
        mem_roles = [m.name for m in ctx.author.roles]
        display = {}
        score = await self.get_user_score(ctx.author.id)
        for x in self.levelsinfo.keys():
            rolename = ctx.guild.get_role(self.levelsinfo[x]).name
            display[x] = rolename
        if not showall:
            embed = discord.Embed(
                title=f'Your current score: {score}',
                description=f'Here are all the roles you have yet to earn.\n'
                            f'To display all roles, including ones you have, run `+levels all`',
                color=discord.Colour.red()
            )
        else:
            embed = discord.Embed(
                title=f'Your current score: {score}',
                description=f'Here are all the roles that can be earned',
                color=discord.Colour.red()
            )
        for i in display.keys():
            if showall:
                embed.add_field(name=display[i], value=f'Score required: **{i}**', inline=False)
            else:
                if display[i] not in mem_roles:
                    embed.add_field(name=display[i], value=f'Score required: **{i}**', inline=False)
        embed.set_thumbnail(url=ctx.author.avatar)
        if ctx.author.premium_since:
            embed.set_footer(text='Thank you for boosting! You are receiving double the points a non-booster would get.')
        else:
            embed.set_footer(text='You are receiving half the points you could be receiving!\n'
                                  'Boost the server today for a sweet x2 points multiplier for the entire time you\'re boosting ;)')
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='justpoints')
    async def justpoints(self,ctx):
        score = await self.get_user_score(ctx.author.id)
        embed = discord.Embed(
            title=f'Your current score: {score}',
            color=discord.Colour.red()
        )
        embed.set_author(name=str(ctx.author), icon_url=ctx.author.avatar)
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='leaderboard')
    async def leaderboard(self, ctx):
        embed = discord.Embed(
            title='Top 5 level leaderboard (excluding admins)',
            color = discord.Colour.red()
        )
        admin_ids = [m.id for m in ctx.guild.members if m.guild_permissions.administrator]
        listings = await self.get_leaderboard(admin_ids)
        for l in listings:
            mem = ctx.guild.get_member(l[0])
            if mem:
                embed.add_field(name=f'@{str(mem)}',value=f'{l[1]} points',inline=False)
        await ctx.send(embed=embed)

    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='lvlthreshold', hidden=True)
    async def lvlthreshold(self, ctx, thresh=None):
        try:
            thresh = int(thresh)
        except:
            await ctx.send(f'Could not convert {thresh} to int')
            return
        if not thresh or thresh < 0:
            await ctx.send('Invalid number')
            return
        lvls = await self.bot.db_conn.execute("SELECT * FROM levels ORDER BY score_needed")
        lvls = await lvls.fetchall()
        changes = 'Changes have been made:\n```\n'
        for x, i in enumerate(lvls):
            scoreneeded = i[0]
            roleid = i[1]
            # ignore first
            if scoreneeded == 1:
                changes += f'{scoreneeded} -> 1\n'
            else:
                await self.bot.db_conn.execute("UPDATE levels SET score_needed = ? WHERE role_id = ?", (thresh * x, roleid))
                changes += f'{scoreneeded} -> {thresh * x}\n'
        changes += '```'
        await self.bot.db_conn.commit()
        await ctx.send(changes)

    def cog_unload(self):
        self.vc_point_update.cancel()
        self.point_decay.cancel()

    @tasks.loop(seconds=60.0)
    async def vc_point_update(self):
        guild = self.bot.get_guild(self.guildid)
        for i in self.active_vc_members:
            mem = guild.get_member(i)
            if mem:
                if not mem.voice.self_deaf:
                    if mem.voice.channel != self.sleep_channel:
                        if mem.voice.self_video:
                            reward = score_per_vc_minute  + random.randint(1, 3)
                        elif mem.voice.self_stream:
                            reward = score_per_vc_minute  + random.randint(0, 2)
                        else:
                            reward = score_per_vc_minute  + random.randint(-2, 2)
                    await self.add_and_check_score(mem,guild,reward)
                    await self.create_or_update_vctime_tracker(mem.id)

    @tasks.loop(hours=24.0)
    async def point_decay(self):
        decayed = ""
        d_amount = 100
        guild = self.bot.get_guild(self.guildid)
        ls = await self.bot.db_conn.execute("SELECT * FROM lastseen_users")
        ls = await ls.fetchall()
        errors = 0
        for m in ls:
            try:
                user = m[0]
                user_score = await self.get_user_score(user)
                if user_score > 0:
                    date_arrowed = arrow.get(m[1], 'MM/DD/YYYY')
                    now = arrow.utcnow()
                    days_since = abs((date_arrowed - now).days) - 1
                    if days_since >= 7:
                        mem = guild.get_member(user)
                        if mem:
                            if not mem.premium_since:
                                await self.add_and_check_score(mem, guild, -d_amount)
                                decayed = decayed + ", " + str(mem)
            except:
                errors += 1


    # begin store code
    #itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text
    async def get_item_details(self, item):
        query = await self.bot.db_conn.execute("SELECT * FROM items WHERE itemid = ?", (item,))
        query = await query.fetchone()
        if query:
            return query
        return None

    async def can_user_afford_item(self, snowflake, item):
        score = await self.get_user_score(snowflake)
        price = await self.get_item_details(item)
        price = int(price[2])
        if score >= price:
            return True
        return False

    async def get_all_user_items(self, snowflake):
        items_query = await self.bot.db_conn.execute("SELECT itemid FROM inventories WHERE snowflake = ?", (snowflake,))
        items_query = await items_query.fetchall()
        # dict of item : quantity
        items = {}
        for i in items_query:
            if i[0] in items:
                items[i[0]] = items[i[0]] + 1
            else:
                items[i[0]] = 1
        return items

    async def does_user_have_item(self, snowflake, item):
        items_query = await self.bot.db_conn.execute("SELECT * FROM inventories WHERE snowflake = ? AND itemid = ?", (snowflake, item))
        items_query = await items_query.fetchall()
        if not items_query:
            return False
        return len(items_query)

    async def get_sell_price(self, item):
        price = await self.get_item_details(item)
        price = price[2]
        return price - (price * 0.4)

    async def give_user_item(self, snowflake, item):
        await self.bot.db_conn.execute("INSERT into inventories VALUES (?, ?, 0)", (snowflake, item))
        await self.bot.db_conn.commit()

    async def remove_user_item(self, snowflake, item, sold, all):
        if not all:
            await self.bot.db_conn.execute("DELETE FROM inventories WHERE snowflake = ? AND itemid = ? LIMIT 1", (snowflake, item))
        else:
            await self.bot.db_conn.execute("DELETE FROM inventories WHERE snowflake = ? AND itemid = ?", (snowflake, item))
        await self.bot.db_conn.commit()
        if sold:
            price = await self.get_sell_price(item)
            await self.modify_user_score(snowflake, price)
    
    # only items with sticky status should touch this
    async def is_item_used(self, snowflake, item):
        items_query = await self.bot.db_conn.execute("SELECT * FROM inventories WHERE snowflake = ? AND itemid = ? AND used = 1", (snowflake, item))
        items_query = await items_query.fetchall()
        if items_query:
            return True
        return False

    @commands.guild_only()
    @commands.command(name='buy', description='Buys an item', usage='+buy itemid',aliases=['purchase'])
    async def buy(self, ctx, item):
        owned = await self.does_user_have_item(ctx.author.id, item)
        item = item.lower()
        item_details = await self.get_item_details(item)
        if not item_details:
            await ctx.reply("This item could not be found.")
            return
        if owned and (owned + 1) > item_details[4]:
            await ctx.reply("You already own the max for this item. Either use, trash, or sell these item(s) before buying more.")
            return
        name = item_details[1]
        price = item_details[2]
        status = await self.can_user_afford_item(ctx.author.id, item)
        if not status:
            await ctx.reply(f"You can not afford this item. It costs {price} points.")
            return
        await self.modify_user_score(ctx.author.id, -price)
        await ctx.reply(f"Congratulations! You now own a {name}. Your account has been charged {price} points.\nYou may view this item in your inventory by typing `+inventory`.\nIf this item is usable, you should use it with `+useitem itemid`.")
        await self.give_user_item(ctx.author.id, item)

    @commands.guild_only()
    @commands.has_guild_permissions(administrator=True)
    @commands.command(name='forcegiveitem', description='Forcibly gives a user an item', usage='+forcegive member itemid')
    async def forcegive(self, ctx, itemid, member:discord.Member=None):
        member = member or ctx.author
        itemid = itemid.lower()
        item_details = await self.get_item_details(itemid)
        if not item_details:
            await ctx.reply("This item could not be found.")
            return
        await self.give_user_item(member.id, itemid)
        await ctx.reply("Item given.")
    
    @commands.guild_only()
    @commands.is_owner()
    #itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text
    @commands.command(name='additem', description='Adds an item to the database', usage='+additem itemid, full item name, price, description, max, sticky, sellable, icon url')
    async def additem(self, ctx, *, content):
        content = content.split(',')
        if len(content) < 8:
            await ctx.reply("Wrong number of arguments.")
            return
        itemid = content[0].strip()
        itemname = content[1].strip()
        price = content[2].strip()
        description = content[3].strip()
        maxct = content[4].strip()
        sticky = content[5].strip()
        sellable = content[6].strip()
        icon = content[7].strip()
        await self.bot.db_conn.execute("INSERT INTO items VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (itemid, itemname, price, description, int(maxct), int(sticky), int(sellable), icon))
        await self.bot.db_conn.commit()
        await ctx.reply("Done: \n" + [i for i in content])

    @commands.guild_only()
    @commands.is_owner()
    #itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text
    @commands.command(name='modifyitem', description='Modifies an item in the database', usage='+modifyitem attribute value')
    async def modifyitem(self, ctx, itemid, attribute, *, value):
        itemid = itemid.lower()
        attr = attribute.lower()
        if attr == "price":
            await self.bot.db_conn.execute("UPDATE items SET price = ? WHERE itemid = ?", (int(value), itemid))
            await self.bot.db_conn.commit()
            await ctx.reply("OK")
        if attr == "name":
            await self.bot.db_conn.execute("UPDATE items SET fullname = ? WHERE itemid = ?", (int(value), itemid))
            await self.bot.db_conn.commit()
            await ctx.reply("OK")
        

    @commands.guild_only()
    @commands.command(name='useitem', description='Uses an item', usage="+useitem itemid")
    async def useitem(self, ctx, itemid):
        success = False
        itemid = itemid.lower()
        item_details = await self.get_item_details(itemid)
        if not item_details:
            await ctx.reply("This item does not exist.")
            return
        if not await self.does_user_have_item(ctx.author.id, itemid):
            await ctx.reply("You do not own this item.")
            return
        if bool(item_details[5]) and await self.is_item_used(ctx.author.id, itemid):
            await ctx.reply("This item has sticky status and has already been used.")
            return
        if itemid == "botsay":
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                await ctx.send("Please enter what you want to be sent from me in #general: ")
                msg = await self.bot.wait_for('message', timeout = 60.0, check=check)
                general = self.bot.get_channel(channel_id_here)
                await general.send(f"{ctx.author.mention}: \"{msg.clean_content}\"")
                success = True
            except asyncio.TimeoutError:
                await ctx.send('You didn\'t answer me in time. Your item has not been used up.')
                return
        elif itemid == "customrole":
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            try:
                await ctx.reply("BEFORE YOU USE THIS: Please note that admins reserve the right to change or remove your role to enforce rules or for other reasons.\nMake sure your role details are what you want, for eternity; there are NO refunds.")
                await ctx.send("Please enter a name for your custom role. Choose wisely; you cannot change this later and mods will likely not change it for you.")
                role_name = await self.bot.wait_for('message', timeout = 120.0, check=check)
                role_name = role_name.content
                if len(role_name) > 20:
                    await ctx.reply("Role names cannot be more than 20 characters. Your item has not been used; please decide a better name and reuse this item.")
                    return
                for c in role_name:
                    if c.lower() not in "abcdefghijklmnopqrstuvwxyz ":
                        await ctx.reply("Role names can only have letters in them. Your item has not been used; please decide a better name and reuse this item.")
                        return
            except asyncio.TimeoutError:
                await ctx.send('You didn\'t answer me in time. Your item has not been used up.')
                return
            try:
                await ctx.send("Please enter a color for your custom role, in hexcode (ie, #fff000).\nUse this picker to choose a color: https://www.google.com/search?q=color+picker/")
                prerole_color = await self.bot.wait_for('message', timeout = 120.0, check=check)
                prerole_color = prerole_color.content
                if 7 < len(prerole_color) < 6:
                    await ctx.reply("Invalid format, this should be at least 6 characters, and at most 7. Your item has not been used, please try again later.")
                    return
                role_color = prerole_color.replace("#", "")
                role_color = int(role_color, 16)
            except asyncio.TimeoutError:
                await ctx.send('You didn\'t answer me in time. Your item has not been used up.')
                return
            
            try:
                embed = discord.Embed(
                    title="Please verify all of these details. If everything looks good, enter \"confirm\". If not, enter \"deny\" or wait 60 seconds till this cancels."
                )
                embed.color = role_color
                embed.add_field(name='Role name', value=role_name)
                embed.add_field(name='Role color', value=prerole_color + " (it\'s the color of this embed)")
                await ctx.send(embed=embed)
                conf = await self.bot.wait_for('message', timeout = 60.0, check=check)
                conf = conf.content.lower()
                if conf == "confirm":
                    await ctx.reply("OK! Making your role now.")
                    role = await ctx.guild.create_role(name=role_name, colour=role_color)
                    position = [r.name for r in ctx.guild.roles].index("Sapphire")
                    await role.edit(position = position)
                    await ctx.author.add_roles(role)
                    await ctx.reply("OK, you\'re all set! Your role has been created and you have been assigned. Enjoy!")
                    success = True
                    # dont have time to debug lol. should work doe
                    try:
                        admin_ch = self.bot.get_channel(channel_id_here)
                        await admin_ch.send(f"{ctx.author.mention} bought a role, {role_name}.")
                    except:
                        pass
                elif conf == "deny":
                    await ctx.reply("Role creation cancelled; your item has not been used up.")
                    return
            except asyncio.TimeoutError:
                await ctx.send('You didn\'t answer me in time. Your item has not been used up.')
                return
            except Exception as e:
                await ctx.send(f"There was a problem, sorry. Your item has not been used.\nError: {str(e)}")
                success = False
                return
        elif itemid == "xbox360":
            if self.xbox360:
                await ctx.reply("Xbox 360 is already active. Please wait a bit.")
                return
            if not ctx.author.voice:
                await ctx.reply("Please join a channel before using this.")
                return
            channel = ctx.author.voice.channel
            old_bitrate = channel.bitrate
            general = self.bot.get_channel(channel_id_here)
            await general.send(f"{ctx.author.mention} activated Xbox 360 chat! This will be in effect for 30 seconds.")
            self.xbox360 = True
            await channel.edit(bitrate = 8000)
            success = True
            await asyncio.sleep(30)
            await channel.edit(bitrate = old_bitrate)
            await general.send(f"Xbox 360 chat has worn off.")
            self.xbox360 = False

        if success:
            if bool(item_details[5]):
                await self.bot.db_conn.execute("UPDATE inventories SET used = 1 WHERE snowflake = ? AND itemid = ?", (ctx.author.id, itemid))
                await self.bot.db_conn.commit()
            else:
                await self.remove_user_item(ctx.author.id, itemid, False, False)
            await ctx.reply("Your item has been used successfully.")
    
    #itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text
    @commands.guild_only()
    @commands.command(name='give', description='Gives away an item', usage="+give user itemid")
    async def use(self, ctx, recipient:discord.Member, itemid):
        if recipient == ctx.author:
            await ctx.reply("You cannot give yourself your own items.")
            return
        itemid = itemid.lower()
        item_details = await self.get_item_details(itemid)
        if not item_details:
            await ctx.reply("This item does not exist.")
            return
        if not self.does_user_have_item(ctx.author.id, itemid):
            await ctx.reply("You do not own this item.")
        if bool(item_details[5]):
            await ctx.reply("This item has a \"stick\" status and cannot be given away.")
            return
        await self.remove_user_item(ctx.author.id, itemid, False, False)
        await self.give_user_item(recipient.id, itemid)
        await ctx.reply(f"Your item has been given to {recipient.mention} successfully!")

    @commands.guild_only()
    @commands.command(name='inventory', description='Shows the items in your inventory', usage='+inventory',aliases=['items'])
    async def inventory(self, ctx, member:discord.Member=None):
        member = member or ctx.author
        quantities = await self.get_all_user_items(member.id)
        if not quantities:
            if member == ctx.author:
                await ctx.reply(f"You have no items.")
            else:
                await ctx.reply(f"{str(member)} has no items.")
            return
        embed = discord.Embed(
            title=f'Inventory of {str(member)}',
            color=discord.Colour.red()
        )
        for i in quantities.keys():
            quant = str(quantities[i])
            details = await self.get_item_details(i)
            builder = ""
            builder += f"\nQuantity: {quant}"
            builder += f"\nItem ID: \"{details[0]}\""
            if bool(details[5]):
                if self.is_item_used(ctx.author.id, i):
                    builder += f"\nUsed: Yes"
                else:
                    builder += f"\nUsed: No"
            embed.add_field(name=details[1], value=builder, inline=False)
        embed.set_footer(text="Use your items with +useitem\nSell them with +sell\nGive them away with +give\nView more info about an item with +iteminfo itemid")
        await ctx.send(embed=embed)

    @commands.guild_only()
    @commands.command(name='iteminfo', description='Shows info on a specific item', usage='+iteminfo')
    async def iteminfo(self, ctx, itemid):
        item = itemid.lower()
        content = await self.get_item_details(item)
        if not content:
            await ctx.reply("This item could not be found.")
            return
        itemid = content[0]
        itemname = content[1]
        price = content[2]
        description = content[3]
        maxct = content[4]
        sticky = content[5]
        sellable = content[6]
        icon = content[7]
        embed = discord.Embed(
            title = itemname,
            description = description,
            color = discord.Colour.red()
        )
        embed.add_field(name="Price", value=str(price) + " points")
        embed.add_field(name="Max quantity", value=maxct)
        embed.add_field(name="Sticky", value=bool(sticky))
        embed.add_field(name="Sellable", value=bool(sellable))
        embed.set_thumbnail(url=icon)
        await ctx.reply(embed=embed)    
    
    @commands.guild_only()
    @commands.command(name='shop', description='Shows items you can buy for points', usage='+shop', aliases=['store'])
    async def shop(self, ctx):
        embed = discord.Embed(
            title = "Land of Lance gift shop",
            description = "Buy something that suits you",
            color = discord.Colour.red()
        )
        query = await self.bot.db_conn.execute("SELECT * FROM items")
        query = await query.fetchall()
        for i in query:
            builder = ""
            builder += f"\"{i[3]}\""
            builder += f"\nItem ID: \"{i[0]}\""
            builder += f"\nPrice: {i[2]} points"
            embed.add_field(name=i[1], value=builder, inline=False)
            #itemid text, fullname text, price integer, description text, max integer, sticky integer, sellable integer, icon text
        embed.set_footer(text="Type +buy itemid to buy an item, or +iteminfo itemid to view more information on a specific item")
        embed.set_thumbnail(url=self.bot.user.avatar.url)
        await ctx.reply(content="**Please note that buying items uses up your score!** If you buy something expensive enough, you may notice your role drop.", embed=embed)    



    @commands.Cog.listener()
    async def on_voice_state_update(self, mem, b, a):
        # create dict entry when user joins
        if not b.channel and a.channel:
            self.active_vc_members.append(mem.id)
        # do timedelta math to check how long they've been in the channel for, then reward
        if b.channel and not a.channel and mem.id in self.active_vc_members:
            self.active_vc_members.remove(mem.id)
