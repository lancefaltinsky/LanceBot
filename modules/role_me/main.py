from itertools import count
import discord
from discord import utils
from discord.ext import commands, tasks
import logging
from datetime import datetime

async def setup(bot):
    await bot.add_cog(RoleMe(bot))


class GenderPickView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)

    async def grant_pronoun_role(self, interaction, user, pronoun):
        member = interaction.guild.get_member(user.id)
        guild_roles = {r.name:r.id for r in interaction.guild.roles}
        if pronoun in guild_roles.keys():
            role = interaction.guild.get_role(guild_roles[pronoun])
        else:
            colors = {
                'He/him': discord.Colour(int('9eceff', 16)),
                'She/her': discord.Colour(int('ff9fef', 16)),
                'They/them': discord.Colour(int('70ffc2', 16)),
            }
            role = await interaction.guild.create_role(name = pronoun, colour = colors[pronoun])
        if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(f'I have removed the {pronoun} pronoun from your roles.', ephemeral = True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f'I have added the {pronoun} pronoun to your roles.', ephemeral=True)

    #async def interaction_check(self, interaction: discord.Interaction):
    
    @discord.ui.button(label='He/him', emoji='♂️', style=discord.ButtonStyle.blurple)
    async def _he_him(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_pronoun_role(interaction, interaction.user, 'He/him')

    @discord.ui.button(label='She/her', emoji='♀️', style=discord.ButtonStyle.blurple)
    async def _she_her(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_pronoun_role(interaction, interaction.user, 'She/her')
    
    @discord.ui.button(label='They/them', emoji = '👤', style=discord.ButtonStyle.blurple)
    async def _they_them(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_pronoun_role(interaction, interaction.user, 'They/them')

class OrientationPickView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=10)

    async def grant_orientation_role(self, interaction, user, orientation):
        member = interaction.guild.get_member(user.id)
        guild_roles = {r.name:r.id for r in interaction.guild.roles}
        mem_roles = [r.name for r in member.roles]
        for r in mem_roles:
            if r in ['Straight', 'Bisexual', 'Gay', 'Lesbian'] and r != orientation:
                await interaction.response.send_message('You may only have 1 sexual orientation at once.', ephemeral = True)
                return
        if orientation in guild_roles.keys():
            role = interaction.guild.get_role(guild_roles[orientation])
        else:
            colors = {
                'Straight': discord.Colour(int('35e6cf', 16)),
                'Bisexual': discord.Colour(int('8135e6', 16)),
                'Gay': discord.Colour(int('e69b35', 16)),
                'Lesbian': discord.Colour(int('c935e6', 16)),
            }
            role = await interaction.guild.create_role(name = orientation, colour = colors[orientation])
        if role in member.roles:
                await member.remove_roles(role)
                await interaction.response.send_message(f'I have removed the {orientation} orientation from your roles.', ephemeral = True)
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f'I have added the {orientation} orientation to your roles.', ephemeral=True)

    #async def interaction_check(self, interaction: discord.Interaction):
    
    @discord.ui.button(label='Straight', style=discord.ButtonStyle.blurple)
    async def _straight(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_orientation_role(interaction, interaction.user, 'Straight')

    @discord.ui.button(label='Bisexual', style=discord.ButtonStyle.blurple)
    async def _bisexual(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_orientation_role(interaction, interaction.user, 'Bisexual')
    
    @discord.ui.button(label='Gay', style=discord.ButtonStyle.blurple)
    async def _gay(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_orientation_role(interaction, interaction.user, 'Gay')
    
    @discord.ui.button(label='Lesbian', style=discord.ButtonStyle.blurple)
    async def _lesbian(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.grant_orientation_role(interaction, interaction.user, 'Lesbian')

class RoleMe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Role selection cog initialized")
        self.bot.loop.create_task(self.connect_db())
    
    async def connect_db(self):
        await self.bot.db_conn.execute("CREATE TABLE IF NOT EXISTS country_role_people (snowflake integer)")
        await self.bot.db_conn.commit()

    def hprint(self, text):
        logging.info(f'[RoleMe]: {text}')

    @commands.command(name='pronouns', aliases = ['pronoun'])
    async def _pronoun_select(self, ctx):
        await ctx.send("Click a pronoun below to add it to your roles. Take as many as you would like. Clicking a pronoun you already have will remove it.", view=GenderPickView())
    
    @commands.command(name='orientations', aliases=['orientation'])
    async def _orientation_select(self, ctx):
        await ctx.send("Click a sexual orientation below to add it to your roles. Clicking an orientation you already have will remove it.", view=OrientationPickView())
    
    
    @commands.command(name='setcountry', aliases=['country'])
    async def _set_country(self, ctx, country_abbrev=None):
        if not country_abbrev:
            await ctx.reply("Please include your country\'s abbreviation when using this command.")
            return
        finds = await self.bot.db_conn.execute("SELECT * FROM country_role_people WHERE snowflake = ?", (ctx.author.id,))
        finds = await finds.fetchall()
        if finds:
            await ctx.reply("You already have a country role.")
            return
        country_abbrev = country_abbrev.upper()
        async with self.bot.aio_session.get(f'https://api.first.org/data/v1/countries?q={country_abbrev}') as q:
            data = await q.json()
            data = data['data']
            if country_abbrev in data:
                country = data[country_abbrev]['country']
            else:
                await ctx.reply(f"Country not found. For a list of country abbreviations, refer to this, under the \"alpha-2\" column: https://en.wikipedia.org/wiki/List_of_ISO_3166_country_codes")
                return
            guild_roles = {r.name:r.id for r in ctx.guild.roles}
            if country in guild_roles.keys():
                role = ctx.guild.get_role(guild_roles[country])
            else:
                role = await ctx.guild.create_role(name = country, colour = discord.Colour(int('ffffff', 16)))
            if role in ctx.author.roles:
                await ctx.reply('You already have that country\'s role!')
                return
            else:
                await ctx.author.add_roles(role)
                await ctx.reply(f'Congrats, you are now a citizen of {country}!')
                await self.bot.db_conn.execute("INSERT INTO country_role_people VALUES (?)", (ctx.author.id,))
                await self.bot.db_conn.commit()

        
#await ctx.bot.tree.sync()
