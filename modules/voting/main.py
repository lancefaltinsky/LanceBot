import discord
from discord import utils
from discord.ext import commands, tasks
import logging
from datetime import datetime

async def setup(bot):
    await bot.add_cog(Voting(bot))


class PollView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.this_poll = {'voters': set(), 'yes': 0, 'no': 0}

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id not in self.this_poll['voters']:
            return True
        else:
            await interaction.response.send_message("You have already participated in this poll", ephemeral = True)
            return False
    
    async def update_message(self, interaction: discord.Interaction):
        embed = interaction.message.embeds[0]
        yeses = self.this_poll['yes']
        nos = self.this_poll['no']
        if yeses > nos:
            embed.color = discord.Colour.green()
        if yeses == nos:
            embed.color = discord.Colour.orange()
        else:
            embed.color = discord.Colour.red()
        yes_perc = round((yeses / (yeses+nos))*100)
        no_perc = round((nos / (yeses+nos))*100)
        embed.description = f'{yeses} votes yes ({yes_perc}%)\n{nos} votes no ({no_perc}%)'
        await interaction.message.edit(embed=embed, view=self)

    @discord.ui.button(label='Yes', style=discord.ButtonStyle.green)
    async def _yes(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.this_poll['voters'].add(interaction.user.id)
        self.this_poll['yes'] = self.this_poll['yes'] + 1
        await interaction.response.send_message('You have voted yes!', ephemeral=True)
        await self.update_message(interaction)

    @discord.ui.button(label='No', style=discord.ButtonStyle.red)
    async def _voteno(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.this_poll['voters'].add(interaction.user.id)
        self.this_poll['no'] = self.this_poll['no'] + 1
        await interaction.response.send_message('You have voted no!', ephemeral=True)
        await self.update_message(interaction)

class Voting(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Voting cog initialized")

    def hprint(self, text):
        logging.info(f'[Voting]: {text}')

    @commands.hybrid_command(name='quickvote')
    async def quickvote(self, ctx, *, question):
        original_embed = discord.Embed(
            title = f'{question}?',
            description = f'0 votes yes (0%) \n0 votes no (0%)',
            color = discord.Colour.orange()
        )
        await ctx.send(embed = original_embed, view=PollView())
        
#await ctx.bot.tree.sync()
