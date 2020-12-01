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
# Import json
import json
# Import RegEx library
import re
# Import Globstar library
import glob

# Get token from environment variables.
TOKEN = os.getenv('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')

# Import configuration data.
import sonnet_cfg

# prefix for the bot
GLOBAL_PREFIX = sonnet_cfg.GLOBAL_PREFIX


# function to get prefix
def get_prefix(client, message):
    prefixes = GLOBAL_PREFIX
    return commands.when_mentioned_or(*prefixes)(client, message)


# Get db handling library
from lib_sql_handler import db_handler, db_error


intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.guilds = True
intents.members = True

# Initialise Discord Client.
Client = commands.Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    status=discord.Status.online,
    intents=intents
)

# Import libraries.
command_modules = []

for f in os.listdir('./cmds'):
    if f.startswith("cmd_") and f.endswith(".py"):
        print(f)
        command_modules.append(importlib.import_module(f[:-3]))

# Clear cache because cache is volatile between versions
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)


# Load blacklist from cache, or load from db if cache isint existant
def load_blacklist(guild_id):
    try:
        with open(f"datastore/{guild_id}.cache.db", "r") as blacklist_cache:
            return json.load(blacklist_cache)
    except FileNotFoundError:
        db = db_handler(f"datastore/{guild_id}.db")
        blacklist = {}
        for i in ["word-blacklist","regex-blacklist"]:
            try:
                blacklist[i] = db.fetch_rows_from_table("config", ["property",i])[0][1]
            except db_error.OperationalError:
                blacklist[i] = ""
            except IndexError:
                blacklist[i] = ""
        if blacklist["regex-blacklist"]:
            blacklist["regex-blacklist"] = [i.split(" ")[1][1:-2] for i in json.loads(blacklist["regex-blacklist"])["blacklist"]]
        else:
            blacklist["regex-blacklist"] = []
        with open(f"datastore/{guild_id}.cache.db", "w") as blacklist_cache:
            json.dump(blacklist, blacklist_cache)
        db.close()
        return blacklist


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
    with db_handler(f"datastore/{message.guild.id}.db") as db:
        db.make_new_table("config",[["property", str, 1], ["value", str]])
        db.make_new_table("infractions", [
        ["infractionID", int, 1],
        ["userID", str],
        ["moderatorID", str], 
        ["type", str],
        ["reason", str], 
        ["timestamp", int]
        ])


# Handle messages.
@Client.event
async def on_message(message):
    # Statistics.
    stats = {"start": round(time.time() * 10000), "end": 0}

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return

    # Load blacklist from cache or db
    stats["start-blacklist"] = round(time.time() * 10000)
    blacklist = (load_blacklist(message.guild.id))

    # Check message agaist word blacklist
    broke_blacklist = False
    word_blacklist = blacklist["word-blacklist"].split(",")
    for i in message.content.split(" "):
        if i in word_blacklist:
            broke_blacklist = True
    
    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        if re.findall(i, message.content):
            broke_blacklist = True
    
    # If blacklist broken generate infraction
    if broke_blacklist:
        for module in command_modules:
            for entry in module.commands:
                if "warn" == entry:
                    await message.delete()
                    await module.commands["warn"]['execute'](message, [int(message.author.id), "[AUTOMOD] Blacklist"], Client, stats, command_modules)
    stats["end-blacklist"] = round(time.time() * 10000)
    
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
                stats["end"] = round(time.time() * 10000)
                await module.commands[entries]['execute'](message, arguments, Client, stats, command_modules)
Client.run(TOKEN, bot=True, reconnect=True)
