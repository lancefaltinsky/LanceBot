import discord
from discord import utils
from discord.ext import commands, tasks
import logging
import random
from aiogtts import aiogTTS
import io
from googlesearch import search

async def setup(bot):
    await bot.add_cog(Fun(bot))

class SecretView(discord.ui.View):
    def __init__(self, secret, owner):
        super().__init__(timeout=None)
        self.secret = secret
        self.secret_owner = owner
        self.reveals = 0
        self.revealed = set()
    
    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id not in self.revealed:
            return True
        else:
            await interaction.response.send_message("You have already revealed this secret", ephemeral = True)
            return False

    @discord.ui.button(label='Reveal secret', style=discord.ButtonStyle.green)
    async def _revealsecret(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.reveals = self.reveals + 1
        self.revealed.add(interaction.user.id)
        await interaction.message.edit(content=f"{self.secret_owner.mention} has posted a hidden message! Click the button below to reveal it...\nRevealed {self.reveals} times", view=self)
        await interaction.response.send_message(f'Secret from {self.secret_owner.mention}: \"{self.secret}\"', ephemeral=True)

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Fun cog initialized")
        self.lastbooed = 0
        self.uwued = set()

    def hprint(self, text):
        logging.info(f'[Fun]: {text}')

    @commands.has_permissions(manage_messages=True)
    @commands.command(name='sayas', hidden = True)
    async def _sayas(self, ctx, member:discord.Member, *, content):
        webhook = await self.bot.setup_utility_webhook(ctx.channel)
        await ctx.message.delete()
        if webhook:
            await webhook.send(content = content, username=member.display_name, avatar_url = member.display_avatar)
        else:
            await ctx.reply("Error")

    
    @commands.command(name='compatibility', description='Shows how compatible 2 members are, in terms of friendship or otherwise')
    async def _compatibility(self, ctx, member1:discord.Member, member2:discord.Member=None):
        if not member2:
            member2 = member1
            member1 = ctx.author
        await ctx.reply(f'{member1.mention} and {member2.mention} are {random.randint(1, 100)}% compatible.')
    
    @commands.command(name='8ball')
    async def _8ball(self, ctx, question):
        choices = [
            "It is certain",
            "There's no doubt about it",
            "You can rely on it",
            "Definitely",
            "It's pretty decidedly so",
            "Yes",
            "Most likely",
            "Outlook looks good",
            "Signs point to yes",
            "Don\'t count on it",
            "Outlook isn\'t good",
            "My sources say no"
        ]
        choice = random.choice(choices)
        await ctx.reply(choice)
    
    async def generate_twoline_meme(self, template, line1, line2=''):
        params = {
            'username': 'API USERNAME HERE',
            'password': 'API PASSWORD HERE', 
            'text0': line1,
            'text1': line2,
            'template_id': template
        }
        async with self.bot.aio_session.post('https://api.imgflip.com/caption_image', params=params) as req:
            resp = await req.json()
            self.hprint(resp)
            return resp['data']['url']

    @commands.command(name='twobuttons', aliases=['cantdecide'], description='Generates a \"two buttons\" meme with given text. Use comma to separate the lines')
    async def _twobuttons(self, ctx, *, text):
        if ',' not in text:
            text += ','
        text = text.split(',')
        url = await self.generate_twoline_meme(87743020, text[0], text[1])
        await ctx.reply(url)
    
    @commands.command(name='distractedboyfriend', description='Generates a \"distracted boyfriend\" meme')
    async def _distracted_bf(self, ctx, *, text):
        if ',' not in text:
            text += ','
        text = text.split(',')
        url = await self.generate_twoline_meme(112126428, text[0], text[1])
        await ctx.reply(url)
    
    @commands.command(name='distractedboyfriend', aliases=['distractedbf'], description='Generates a \"change my mind\" meme')
    async def _distracted_bf(self, ctx, *, text):
        url = await self.generate_twoline_meme(129242436, text)
        await ctx.reply(url)
    
    async def generate_tts(self, slow, language, query, tld='com'):
        fp = io.BytesIO()
        await aiogTTS().write_to_fp(query, fp, slow=slow, lang=language, tld=tld)
        fp.seek(0)
        return fp
    
    @commands.cooldown(1, 30, type=commands.BucketType.user)
    @commands.command(name='tts', description='Generates a text-to-speech file based off the given message')
    async def _lancetts(self, ctx, *, text):
        async with ctx.typing():
            fp = await self.generate_tts(False, 'en', text)
            await ctx.send(file=discord.File(fp, filename="tts.mp3"))
    
    @commands.has_guild_permissions(manage_messages=True)
    @commands.command(name='sayin')
    async def _say_in(self, ctx, channel:discord.TextChannel, *, content):
        await channel.send(content)
        await ctx.message.add_reaction('✅')
    
    
    @commands.has_guild_permissions(manage_messages=True)
    @commands.command(name='dm')
    async def _bot_dm(self, ctx, channel:discord.Member, *, content):
        await channel.send(content)
        await ctx.message.add_reaction('✅')
    
    @commands.command(name='error', description='Literally just for testing the error handler')
    async def _make_errror(self, ctx):
        await ctx.reply(1 + '1')
    
    @commands.hybrid_command(name='secret')
    async def _secret(self, ctx, *, secret):
        await ctx.send(f"{ctx.author.mention} has posted a hidden message! Click the button below to reveal it...\nRevealed 0 times", view=SecretView(secret, ctx.author))
        await ctx.message.delete()
    
    def get_google_result(self, query):
        results = search(query, num_results=1)
        if not results:
            return "No results"
        return list(results)[0]


    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot:
            return
        if not msg.guild:
            return
            #return await self.bot.get_channel(972719693628571658).send(f'Message from {msg.author.mention}: {msg.clean_content}')
        if msg.channel.id == 980702074771767337:
            async with msg.channel.typing():
                res = await self.bot.loop.run_in_executor(None, self.get_google_result, msg.clean_content)
                return await msg.reply(res)