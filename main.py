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
command_modules_dict = {}
for f in os.listdir('./cmds'):
    if f.startswith("cmd_") and f.endswith(".py"):
        print(f)
        command_modules.append(importlib.import_module(f[:-3]))
for module in command_modules:
    command_modules_dict.update(module.commands)

# Clear cache because cache is volatile between versions
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)

# Import blacklist loader
from lib_load_blacklist import load_blacklist


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

    # Warn if user is not bot
    if not Client.user.bot:
        print("WARNING: The connected account is not a bot, as it is against ToS we do not condone user botting")


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
    stats = {"start": round(time.time() * 100000), "end": 0}
    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return

    # Ignore message if author is a bot
    if message.author.bot:
        return

    # Load blacklist from cache or db
    stats["start-blacklist"] = round(time.time() * 100000)
    blacklist = (load_blacklist(message.guild.id))

    # Check message agaist word blacklist
    broke_blacklist = False
    infraction_type = []
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in message.content.split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append("Word")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        if re.findall(i, message.content):
            broke_blacklist = True
            infraction_type.append("RegEx")

    # Check against filetype blacklist ##NOT IMPLEMENTED YET##
    filetype_blacklist = blacklist["filetype-blacklist"]
    if filetype_blacklist and message.attachments:
        for i in message.attachments:
            for a in filetype_blacklist:
                if i.filename.endswith(a):
                    broke_blacklist = True
                    infraction_type.append("FileType")
    stats["end-blacklist"] = round(time.time() * 100000)

    # If blacklist broken generate infraction
    if broke_blacklist:
        await message.delete()
        await command_modules_dict['warn']['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], Client, stats, command_modules)

    # Check if this is meant for us.
    if not message.content.startswith(GLOBAL_PREFIX):
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][1:len(arguments[0])]

    # Remove command from the arguments.
    del arguments[0]

    # Shoddy code for shoddy business. Less shoddy then before, but still shoddy.
    if command in command_modules_dict.keys():
        stats["end"] = round(time.time() * 100000)
        await command_modules_dict[command]['execute'](message, arguments, Client, stats, command_modules)


Client.run(TOKEN, bot=True, reconnect=True)
