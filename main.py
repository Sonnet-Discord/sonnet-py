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


# Returns specified config from db
def return_config(cur, target):
    try:
        cur.execute("SELECT value FROM config WHERE property = ?", (target,))
        data = cur.fetchone()
        if data:
            return data[0]
        else:
            return ""
    except sqlite3.OperationalError:
        return ""


# Load blacklist from cache, or load from db if cache isint existant
def load_blacklist(guild_id):
    try:
        with open(f"datastore/{guild_id}.cache.db", "r") as blacklist_cache:
            return json.load(blacklist_cache)
    except FileNotFoundError:
        con = sqlite3.connect(f"datastore/{guild_id}.db")
        cur = con.cursor()
        blacklist = {
            "word-blacklist":return_config(cur, "word-blacklist"),
            "regex-blacklist":return_config(cur, "regex-blacklist")
        }
        con.close()
        if blacklist["regex-blacklist"]:
            blacklist["regex-blacklist"] = [i.split(" ")[1][1:-2] for i in json.loads(blacklist["regex-blacklist"])["blacklist"]]
        else:
            blacklist["regex-blacklist"] = []           
        with open(f"datastore/{guild_id}.cache.db", "w") as blacklist_cache:
            json.dump(blacklist, blacklist_cache)
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
    con = sqlite3.connect(f'datastore/{guild.id}.db')
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS config (property TEXT PRIMARY KEY, value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS infractions (infractionID INTEGER PRIMARY KEY, userID TEXT, moderatorID 
    TEXT, type TEXT, reason TEXT, timestamp INTEGER)''')
    con.close()


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
                    await module.commands["warn"]['execute'](message, [str(message.author.id), "[AUTOMOD] Blacklist"], Client, stats, command_modules)
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
