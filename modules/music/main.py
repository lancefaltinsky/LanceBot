import discord
from discord import utils
from discord.ext import commands, tasks
import logging
#import asyncio
import wavelink
import os

async def setup(bot):
    await bot.add_cog(Music(bot))

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.hprint("Music cog initialized")
        self.play_icon = '▶️'
        self.pause_icon = '⏸️'
        self.wave_icon = '👋'
        self.ff_icon = '⏩'
        #self.player = None
        bot.loop.create_task(self.connect_nodes())

    def hprint(self, text):
        logging.info(f'[Music]: {text}')
    
    @commands.Cog.listener()
    async def on_wavelink_track_start(self, player, track):
        self.hprint(f"A track has started: {str(track)}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, player, track, reason):
        if not player.queue.is_empty:
            next = await player.queue.get_wait()
            await player.play(next)

    @commands.Cog.listener()
    async def on_wavelink_track_stuck(self, player, track):
        self.hprint(f"A track is stuck: {str(track)}")
        await self.on_wavelink_track_end(player, track, "Track stuck")

    async def connect_nodes(self):
        await self.bot.wait_until_ready()
        #for c in self.bot.voice_clients:
        #    await c.disconnect()
        await wavelink.NodePool.create_node(bot=self.bot, host='0.0.0.0', port=2333, password="a_decent_password_here")
    
    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, node: wavelink.Node):
        self.hprint(f'Node: <{node.identifier}> is ready!')
    
    async def play_audio(self, ctx, track):
        if not ctx.author.voice:
            return await ctx.reply("You must be in a voice channel to play music!")
        if ctx.voice_client and not ctx.guild.me.voice:
            await ctx.voice_client.disconnect()
        player: wavelink.Player = ctx.voice_client or await ctx.author.voice.channel.connect(cls=wavelink.Player)
        if ctx.author.voice.channel is not player.channel:
            if len(ctx.me.voice.channel.members) == 1:
                await player.move_to(ctx.author.voice.channel)
            else:
                return await ctx.reply(f"You are in a different channel than the bot, and there are currently people using it (in {player.user.voice.channel.mention}). Please join their voice channel to use music commands.")

        await ctx.guild.me.edit(deafen=True)
        if player.queue.is_empty and not player.is_playing():
            await player.play(track)
            await ctx.message.add_reaction(self.play_icon)
        else:
            await player.queue.put_wait(track)
            embed = discord.Embed(
                title = 'Track queued',
                description = f"[{track.title or 'Unknown/local track'}]({track.uri or ' '})",
                color = discord.Colour.purple()
            )
            embed.set_footer(text='Getting music videos or unrelated videos? Try adding the word \"audio\" to the end of your search.')
            await ctx.reply(embed = embed)

    @commands.command(name='play', aliases=['p'], description='Plays a track', usage='+p query')
    async def _play(self, ctx: commands.Context, *, search: wavelink.YouTubeTrack):
        await self.play_audio(ctx, search)

    @commands.command(name='sound', description = 'Plays a soundboard sound', usage = '+sound sound name')
    async def _soundboard_play(self, ctx, *, sound = ''):
        sound = sound.replace(' ', '_')
        sound = sound.replace('.mp3', '')
        sound = await wavelink.LocalTrack.search(query=f'./sounds/{sound}.mp3')
        if sound:
            await self.play_audio(ctx, sound[0])
        else:
            def sound_only(x):
                return x.endswith('.mp3')
            possible_sounds = '\n'.join([f.replace('.mp3', '') for f in filter(sound_only, os.listdir('./modules/music/sounds'))])
            await ctx.reply(f'Sound not found. Possible sounds:\n{possible_sounds}')


    @commands.command(name='queue', aliases=['q', 'np'], description = 'Shows the current queue', usage = '+queue')
    async def _music_queue(self, ctx):
        if not ctx.voice_client:
            return await ctx.reply("I am not actively playing anything.")
        vc = ctx.voice_client
        if vc.queue.is_empty:
            desc = "The queue is currently empty."
        else:
            desc = '\n'.join(f"{x}: [{t.title or 'Unknown/local file'}]({t.uri or ' '})" for x, t in enumerate(vc.queue, 1))
        
        embed = discord.Embed(
            description = desc,
            color = discord.Colour.purple()
        )
        if vc.track:
            embed.set_author(name = f'Currently playing: \"{vc.track.title}\"', url=vc.track.uri)
        else:
            embed.set_author(name='Currently playing: Nothing')
        await ctx.reply(embed = embed)
    
    @commands.command(name='skip', description = 'Skips the current track', usage = '+skip')
    async def _skip_track(self, ctx):
        if not ctx.voice_client:
            return await ctx.reply("I am not actively playing anything.")
        vc = ctx.voice_client
        await vc.stop()
        await ctx.message.add_reaction(self.ff_icon)

    @commands.command(name='stop', aliases=['leave'], description = 'Stops the player', usage='+stop')
    async def _stop_player(self, ctx):
        if not ctx.voice_client:
            return await ctx.reply("I am not currently active.")
        ctx.voice_client.queue.clear()
        await ctx.voice_client.disconnect()
        await ctx.message.add_reaction(self.wave_icon)
    
    @commands.command(name='pause', description = 'Pauses the player', usage = '+pause')
    async def _pause_player(self, ctx):
        if not ctx.voice_client:
            return await ctx.reply("I am not currently active.")
        if ctx.voice_client.is_paused():
            await ctx.reply("I am already paused.")
        else:
            await ctx.voice_client.pause()
            await ctx.message.add_reaction(self.pause_icon)
    
    @commands.command(name='resume', description = 'Resumes the player from a pause', usage = '+resume')
    async def _resume_player(self, ctx):
        if not ctx.voice_client:
            await ctx.reply("I am not currently active.")
        if not ctx.voice_client.is_paused():
            await ctx.reply("I am not currently paused.")
        else:
            await ctx.voice_client.resume()
            await ctx.message.add_reaction(self.play_icon)
    
    @commands.is_owner()
    @commands.command(name='volume')
    async def _player_volume(self, ctx, vol:int):
        if vol < 0 or vol > 1000:
            return await ctx.reply("Volume must be between 0 and 1000.")
        if not ctx.voice_client:
            await ctx.reply("I am not currently active.")
        vc = ctx.voice_client
        await vc.set_volume(vol)
        await ctx.reply(f'Volume set to {vol}')