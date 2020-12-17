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
from lib_mdb_handler import db_handler, db_error


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


# Import blacklist loader
from lib_loaders import load_blacklist

# Import blacklist parser and message skip parser
from lib_parsers import parse_blacklist, parse_skip_message

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
    with db_handler() as db:
        db.make_new_table(f"{message.guild.id}_config",[["property", str, 1], ["value", str]])
        db.make_new_table(f"{message.guild.id}_infractions", [
        ["infractionID", str, 1],
        ["userID", str],
        ["moderatorID", str],
        ["type", str],
        ["reason", str],
        ["timestamp", int]
        ])


# Handle message deletions
@Client.event
async def on_message_delete(message):

    # Ignore bots
    if parse_skip_message(Client, message):
        return

    # Add to log
    with db_handler() as db:
       message_log = db.fetch_rows_from_table(f"{message.guild.id}_config", ["property", "message-log"])
    if message_log:
        message_log = Client.get_channel(int(message_log[0][1]))
        if message_log:
            message_embed = discord.Embed(title="Message Deleted", description=f"Deleted Message in <#{message.channel.id}>", color=0xd62d20)
            message_embed.add_field(name="User", value=f"<@!{message.author.id}>", inline=False)
            message_embed.add_field(name="Message ID", value=f"{message.id}", inline=False)
            message_embed.add_field(name="Message", value=message.content, inline=False)
            await message_log.send(embed=message_embed)


@Client.event
async def on_message_edit(old_message, message):

    # Ignore bots
    if parse_skip_message(Client, message):
        return

    # Add to log
    with db_handler() as db:
       message_log = db.fetch_rows_from_table(f"{message.guild.id}_config", ["property", "message-log"])
    if message_log:
        message_log = Client.get_channel(int(message_log[0][1]))
        if message_log:
            message_embed = discord.Embed(title="Message Edited", description=f"Edited Message in <#{message.channel.id}>", color=0x0057e7)
            message_embed.add_field(name="User", value=f"<@!{message.author.id}>", inline=False)
            message_embed.add_field(name="Message ID", value=f"{message.id}", inline=False)
            message_embed.add_field(name="Old Message", value=old_message.content, inline=False)
            message_embed.add_field(name="Edited Message", value=message.content, inline=False)
            await message_log.send(embed=message_embed)

    # Check against blacklist
    blacklist = load_blacklist(message.guild.id)
    broke_blacklist, infraction_type = parse_blacklist(message, blacklist)

    if broke_blacklist:
        await message.delete()
        await command_modules_dict['warn']['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], Client, stats, command_modules)


# Handle messages.
@Client.event
async def on_message(message):
    # Statistics.
    stats = {"start": round(time.time() * 100000), "end": 0}

    if parse_skip_message(Client, message):
        return

    # Load blacklist
    stats["start-load-blacklist"] = round(time.time() * 100000)
    blacklist = load_blacklist(message.guild.id)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against blacklist
    stats["start-blacklist"] = round(time.time() * 100000)
    broke_blacklist, infraction_type = parse_blacklist(message, blacklist)
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
    command = arguments[0][1:]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict.keys():
        stats["end"] = round(time.time() * 100000)
        try:
            await command_modules_dict[command]['execute'](message, arguments, Client, stats, command_modules)
        except Exception as e:
            await message.channel.send(f"FATAL ERROR in {command}\nPlease contact bot owner")
            raise e


Client.run(TOKEN, bot=True, reconnect=True)

# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
