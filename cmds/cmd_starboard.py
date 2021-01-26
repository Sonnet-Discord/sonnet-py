# Starboard system
# Ultrabear 2020

import importlib

from sonnet_cfg import STARBOARD_EMOJI, DB_TYPE

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_parsers
importlib.reload(lib_parsers)
import lib_loaders
importlib.reload(lib_loaders)

from lib_parsers import parse_boolean, update_log_channel
from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config


async def starboard_channel_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "starboard-channel")
    except RuntimeError:
        return


async def set_starboard_emoji(message, args, client, **kwargs):

    if args:
        emoji = args[0]
    else:
        emoji = load_message_config(message.guild.id, kwargs["ramfs"])["starboard-emoji"]

    with db_hlapi(message.guild.id) as database:
        database.add_config("starboard-emoji", emoji)

    await message.channel.send(f"Updated starboard emoji to {emoji}")


async def set_starboard_use(message, args, client, **kwargs):

    if args:
        gate = parse_boolean(args[0])
    else:
        gate = bool(int(load_message_config(message.guild.id, kwargs["ramfs"])["starboard-enabled"]))

    with db_hlapi(message.guild.id) as database:
        database.add_config("starboard-enabled", int(gate))

    await message.channel.send(f"Starboard set to {bool(gate)}")


async def set_starboard_count(message, args, client, **kwargs):

    if args:

        try:
            count = int(float(args[0]))

            with db_hlapi(message.guild.id) as database:
                database.add_config("starboard-count", count)

            await message.channel.send(f"Starboard count set to {count}")

        except ValueError:
            await message.channel.send("Invalid input, please enter a number")

    else:
        count = load_message_config(message.guild.id, kwargs["ramfs"])["starboard-count"]
        await message.channel.send(f"Starboard count is {count}")


category_info = {'name': 'starboard', 'pretty_name': 'Starboard', 'description': 'Starboard commands.'}

commands = {
    'starboard-channel': {
        'pretty_name': 'starboard-channel <channel>',
        'description': 'Change Starboard',
        'permission': 'administrator',
        'cache': 'keep',
        'execute': starboard_channel_change
        },
    'starboard-emoji': {
        'pretty_name': 'starboard-emoji <emoji>',
        'description': 'Set the starboard emoji',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': set_starboard_emoji
        },
    'starboard-enabled':
        {
            'pretty_name': 'starboard-enabled <boolean value>',
            'description': 'Toggle starboard on or off',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_starboard_use
            },
    'starboard-count':
        {
            'pretty_name': 'starboard-count <number>',
            'description': 'Set starboard reaction count threshold',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_starboard_count
            }
    }

version_info = "1.1.3-DEV"
