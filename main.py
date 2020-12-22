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
TOKEN = os.getenv('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')

# Import configuration data.
import sonnet_cfg

# prefix for the bot
GLOBAL_PREFIX = sonnet_cfg.GLOBAL_PREFIX


# function to get prefix
def get_prefix(client, message):
    prefixes = GLOBAL_PREFIX
    return commands.when_mentioned_or(*prefixes)(client, message)


# Get db handling library
from lib_mdb_handler import db_handler, db_error, db_hlapi


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
for f in os.listdir('./cmds'):
    if f.startswith("cmd_") and f.endswith(".py"):
        print(f)
        command_modules.append(importlib.import_module(f[:-3]))
for module in command_modules:
    command_modules_dict.update(module.commands)


# Import blacklist loader
from lib_loaders import load_message_config

# Import blacklist parser and message skip parser
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions

# Initalize RAM FS
from lib_ramfs import ram_filesystem
ramfs = ram_filesystem()
ramfs.mkdir("datastore")

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
        db.make_new_table(f"{guild.id}_config",[["property", tuple, 1], ["value", str]])
        db.make_new_table(f"{guild.id}_infractions", [
        ["infractionID", tuple, 1],
        ["userID", str],
        ["moderatorID", str],
        ["type", str],
        ["reason", str],
        ["timestamp", int(64)]
        ])
        db.make_new_table(f"{guild.id}_starboard", [["messageID", tuple, 1]])
        db.make_new_table(f"{guild.id}_mutes", [["infractionID", tuple, 1],["userID", str],["endMute",int(64)]])


# Handle starboard system
@Client.event
async def on_reaction_add(reaction, user):
    mconf = load_message_config(reaction.message.guild.id, ramfs)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        with db_hlapi(reaction.message.guild.id) as db:
            channel_id = db.grab_config("archive-channel")
            if channel_id:

                channel = Client.get_channel(int(channel_id))
                in_board = db.in_starboard(reaction.message.id)
                if channel and not(in_board):

                    db.add_to_starboard(reaction.message.id)
                    starboard_embed = discord.Embed(title="Starred message",description=reaction.message.content, url=reaction.message.jump_url, color=0xffa700)
                    starboard_embed.set_author(name=reaction.message.author, icon_url=reaction.message.author.avatar_url)
                    starboard_embed.timestamp = datetime.now()

                    await channel.send(embed=starboard_embed)


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
            message_embed = discord.Embed(title=f"Message deleted in #{message.channel}", description=message.content, color=0xd62d20)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.now()
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
            message_embed = discord.Embed(title=f"Message edited in #{message.channel}", color=0xffa700)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)
            message_embed.add_field(name="Old Message", value=old_message.content, inline=False)
            message_embed.add_field(name="New Message", value=message.content, inline=False)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.now()
            await message_log.send(embed=message_embed)

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, infraction_type = parse_blacklist(message, mconf)

    if broke_blacklist:
        try:
            await message.delete()
        except discord.errors.Forbidden:
            pass
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], Client, stats, command_modules)


# Handle messages.
@Client.event
async def on_message(message):
    # Statistics.
    stats = {"start": round(time.time() * 100000), "end": 0}

    if parse_skip_message(Client, message):
        return

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against blacklist
    stats["start-blacklist"] = round(time.time() * 100000)
    broke_blacklist, infraction_type = parse_blacklist(message, mconf)
    stats["end-blacklist"] = round(time.time() * 100000)

    # If blacklist broken generate infraction
    if broke_blacklist:
        try:
            await message.delete()
        except discord.errors.Forbidden:
            pass
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], Client, stats, command_modules)

    # Check if this is meant for us.
    if not message.content.startswith(mconf["prefix"]):
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][len(mconf["prefix"]):]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict.keys():
        permission = await parse_permissions(message, command_modules_dict[command]['permission'])
        try:
            if permission:
                stats["end"] = round(time.time() * 100000)
                await command_modules_dict[command]['execute'](message, arguments, Client, stats, command_modules)
        # Correct dberrors
        except db_error.OperationalError:
            await message.channel.send("Database missing components, rebuilding")
            await command_modules_dict["recreate-db"]['execute'](message, 1, Client, stats, command_modules)
            if permission:
                await command_modules_dict[command]['execute'](message, arguments, Client, stats, command_modules)
        except Exception as e:
            await message.channel.send(f"FATAL ERROR in {command}\nPlease contact bot owner")
            raise e
        if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
            ramfs.remove_f(f"datastore/{message.guild.id}.cache.db")
            if command_modules_dict[command]['cache'] == "regenerate":
                load_message_config(message.guild.id, ramfs)

Client.run(TOKEN, bot=True, reconnect=True)

# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
