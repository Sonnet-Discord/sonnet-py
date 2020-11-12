# OS library.
import os

# Start Discord.py
import discord

# Prepare to load environment variables.
from dotenv import load_dotenv
# Load environment variables.
load_dotenv()
# Get token from environment variables.
TOKEN = os.getenv('RHEA_TOKEN')

# Initialise system library for editing PATH.
import sys
# Initialise time for health monitoring.
import time

# insert at 1, 0 is the script path (or '' in REPL)
sys.path.insert(1, os.getcwd() + '/cmds')

# Initialise Discord Client.
client = discord.Client()

# Import libraries. Make more efficient in future.
import cmd_utils

# Catch errors without being fatal - log them.
@client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            raise

# Bot connected to Discord.
@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

# Handle messages.
@client.event
async def on_message(message):
    # Statistics.
    stats = {"start": 0, "end": 0}

    # Add start point to stats.
    stats["start"] = int(round(time.time() * 1000))

    # Make sure we don't start a feedback loop.
    if message.author == client.user:
      return
      
    #print(message)

    # Check if this is meant for us.
    if message.content[0] != "!":
      return

    # Split into cmds and arguments.
    arguments = message.content.split();
    command = arguments[0][1:len(arguments[0])];
    
    # Remove command from the arguments.
    del arguments[0]

    # Shoddy code for shoddy business.
    for entries in cmd_utils.commands:
      if command == entries:
        stats["end"] = int(round(time.time() * 1000))
        await cmd_utils.commands[entries]['execute'](message, client,stats)


client.run(TOKEN)