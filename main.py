# OS library.
import os

# Start Discord.py
import discord
from discord.ext import commands

# Initialise system library for editing PATH.
import sys
# Initialise time for health monitoring.
import time

# Get token from environment variables.
TOKEN = os.getenv('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')


# function to get prefix
def get_prefix(client, message):
    prefixes = "!"
    return commands.when_mentioned_or(*prefixes)(client, message)


# Initialise Discord Client.
Client = commands.Bot(
    command_prefix=get_prefix,
    case_insensitive=True,
    status=discord.Status.online
)

# Import libraries. Make more efficient in future.
import cmd_utils


# Catch errors without being fatal - log them.
@Client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise


# Bot connected to Discord.
@Client.event
async def on_ready():
    print(f'{Client.user} has connected to Discord!')


# Handle messages.
@Client.event
async def on_message(message):
    # Statistics.
    stats = {"start": int(round(time.time() * 1000)), "end": 0}

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return

    # Check if this is meant for us.
    if message.content[0] != "!":
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][1:len(arguments[0])]

    # Remove command from the arguments.
    del arguments[0]

    # Shoddy code for shoddy business.
    for entries in cmd_utils.commands:
        if command == entries:
            stats["end"] = int(round(time.time() * 1000))
            await cmd_utils.commands[entries]['execute'](message, Client, stats)


Client.run(TOKEN, bot=True, reconnect=True)
