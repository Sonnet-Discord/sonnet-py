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
# Import Globstar library
import glob
# Import datetime for message logging
from datetime import datetime

# Get token from environment variables.
TOKEN = os.environ.get('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')
sys.path.insert(1, os.getcwd() + '/dlibs')

# Import configuration data.
import sonnet_cfg

# prefix for the bot
GLOBAL_PREFIX = sonnet_cfg.GLOBAL_PREFIX


# function to get prefix
def get_prefix(client, message):
    prefixes = GLOBAL_PREFIX
    return commands.when_mentioned_or(*prefixes)(client, message)


# Get db handling library
from lib_db_obfuscator import db_hlapi

intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.guilds = True
intents.members = True
intents.reactions = True

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
dynamiclib_modules = []
dynamiclib_modules_dict = {}

def sonnet_load_command_modules():
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()
    # Init imports
    for f in os.listdir('./cmds'):
        if f.startswith("cmd_") and f.endswith(".py"):
            print(f)
            command_modules.append(importlib.import_module(f[:-3]))
    for f in os.listdir("./dlibs"):
        if f.startswith("dlib_") and f.endswith(".py"):
            print(f)
            dynamiclib_modules.append(importlib.import_module(f[:-3]))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)
    for module in dynamiclib_modules:
        dynamiclib_modules_dict.update(module.commands)

sonnet_load_command_modules()

def sonnet_reload_command_modules():
    print("Reloading Kernel Modules")
    # Init vars
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules_dict = {}
    dynamiclib_modules_dict = {}
    # Update set
    for i in range(len(command_modules)):
            command_modules[i] = (importlib.reload(command_modules[i]))
    for i in range(len(dynamiclib_modules)):
            dynamiclib_modules[i] = (importlib.reload(dynamiclib_modules[i]))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)
    for module in dynamiclib_modules:
        dynamiclib_modules_dict.update(module.commands)

# Generate debug command subset
debug_commands = {"debug-modules-load":sonnet_load_command_modules, "debug-modules-reload":sonnet_reload_command_modules}

# Import blacklist loader
from lib_loaders import load_message_config

# Import blacklist parser and message skip parser
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions

# Initalize RAM FS
from lib_ramfs import ram_filesystem
ramfs = ram_filesystem()
ramfs.mkdir("datastore")

def regenerate_ramfs():
    global ramfs
    ramfs = ram_filesystem()
    ramfs.mkdir("datastore")

debug_commands["debug-drop-cache"] = regenerate_ramfs

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
    with db_hlapi(guild.id) as db:
        db.create_guild_db()


# Handle starboard system
@Client.event
async def on_reaction_add(reaction, user):
    try:
        await dynamiclib_modules_dict["on-reaction-add"](reaction, Client, ramfs)
    except Exception as e:
        await reaction.message.channel.send(f"FATAL ERROR in on-reaction-add\nPlease contact bot owner")
        raise e


# Handle message deletions
@Client.event
async def on_message_delete(message):
    try:
        await dynamiclib_modules_dict["on-message-delete"](message, Client)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message-delete\nPlease contact bot owner")
        raise e


@Client.event
async def on_message_edit(old_message, message):
    try:
        await dynamiclib_modules_dict["on-message-edit"](old_message, message, Client, command_modules, command_modules_dict, ramfs)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message-edit\nPlease contact bot owner")
        raise e


# Handle messages.
@Client.event
async def on_message(message):

    # If bot owner run a debug command
    if message.content in debug_commands.keys() and sonnet_cfg.BOT_OWNER and message.author.id == int(sonnet_cfg.BOT_OWNER):
        debug_commands[message.content]()
        await message.channel.send("Debug command has run")
        return

    try:
        await dynamiclib_modules_dict["on-message"](message, Client, command_modules, command_modules_dict, ramfs)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message\nPlease contact bot owner")
        raise e


Client.run(TOKEN, bot=True, reconnect=True)

# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
