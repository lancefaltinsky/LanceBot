import discord
from discord.ext import commands
from discord.ext.commands import CommandNotFound
import logging
from configparser import ConfigParser
import aiohttp
import aiosqlite
from datetime import datetime
from os import getcwd
logging.basicConfig(level=logging.INFO)
config = ConfigParser()
config.read('config.ini')
default_prefix = str(config['lancebot']['default_prefix'])
bot_name = str(config['lancebot']['bot_name'])
client_id = str(config['lancebot']['client_id'])
token = str(config['lancebot']['token'])
perms = int(config['lancebot']['perms'])

class Lancebot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def hprint(self, text):
        logging.info(f"[{bot_name} core]: {text}")
    
    async def on_ready(self):
        invlink = f"https://discord.com/oauth2/authorize?client_id={client_id}&permissions={perms}&scope=bot"
        self.prefix = default_prefix
        self.name = bot_name
        self.hprint("Creating AIO session...")
        self.aio_session = aiohttp.ClientSession()
        self.hprint("AIO session created")
        self.hprint("Connecting to database...")
        self.db_conn = await aiosqlite.connect('lancebot.db')
        self.hprint("DB connection established, setting journal mode to WAL...")
        await self.db_conn.execute('PRAGMA journal_mode=WAL')
        await self.db_conn.commit()
        self.hprint("Committed")
        self.launch_time = datetime.utcnow()
        self.hprint("Initiating module handler...")
        await bot.load_extension('modules.module_handler.main')
        self.hprint(f"{bot_name} is ready, invite me at link {invlink}")
    
    async def start(self, *args, **kwargs):
        self.hprint("Starting")
        await super().start(*args, **kwargs)
    
    async def setup_utility_webhook(self, channel):
        WEBHOOK_NAME = 'Lancebot webhook'
        try:
            webhooks = await channel.webhooks()
            for w in webhooks:
                if w.name ==  WEBHOOK_NAME:
                    return w
            return await channel.create_webhook(name=WEBHOOK_NAME, avatar=None, reason=f'For {bot_name} utility purposes')
        except:
            return None
    
    async def close(self):
        self.hprint(f"{bot_name} is stopping!")
        self.hprint("Closing AIO session...")
        await self.aio_session.close()
        self.hprint("Closing database connection...")
        await self.db_conn.close()
        self.hprint("Closing bot loop..")
        await super().close()


intents = discord.Intents.all()
#intents.members = True
#intents.messages = True

bot = Lancebot(command_prefix=default_prefix, intents=intents, help_command=None)
bot.run(token)