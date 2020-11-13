# OS library.
import os

# Get importlib.
import importlib

# Start Discord.py
import discord
from discord.ext import commands

# Initialise system library for editing PATH.
import sys
# Initialise time for health monitoring.
import time
# Import sqlite3
import sqlite3

# Get token from environment variables.
TOKEN = os.getenv('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')

# prefix for the bot
GLOBAL_PREFIX = "!"


# function to get prefix
def get_prefix(client, message):
    prefixes = GLOBAL_PREFIX
    return commands.when_mentioned_or(*prefixes)(client, message)


intents = discord.Intents.default()
intents.typing = False
intents.presences = False
intents.guilds = True


# Initialise Discord Client.
Client = commands.Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    status=discord.Status.online,
    intents=intents
)

# Import libraries. Make more efficient in future.
import cmd_utils
import cmd_moderation

command_modules = [cmd_utils, cmd_moderation]


# Catch errors without being fatal - log them.
@Client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
            raise
        else:
            raise


# Bot connected to Discord.
@Client.event
async def on_ready():
    print(f'{Client.user} has connected to Discord!')


# Bot joins a guild
@Client.event
async def on_guild_join(guild):
    con = sqlite3.connect(f'datastore/{guild.id}.db')
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS config (property TEXT PRIMARY KEY, value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS infractions (infractionID INTEGER PRIMARY KEY, userID TEXT, moderatorID 
    TEXT, type TEXT, reason TEXT, timestamp INTEGER)''')


# Handle messages.
@Client.event
async def on_message(message):
    # Statistics.
    stats = {"start": int(round(time.time() * 1000)), "end": 0}

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return

    # Check if this is meant for us.
    if not message.content.startswith(GLOBAL_PREFIX):
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][1:len(arguments[0])]

    # Remove command from the arguments.
    del arguments[0]

    # Shoddy code for shoddy business. Less shoddy then before, but still shoddy.
    for module in command_modules:
        for entries in module.commands:
            if command == entries:
                stats["end"] = int(round(time.time() * 1000))
                await module.commands[entries]['execute'](message, Client, stats)


Client.run(TOKEN, bot=True, reconnect=True)
