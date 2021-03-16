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
from lib_loaders import load_message_config
from lib_db_obfuscator import db_hlapi

from sonnet_cfg import STARBOARD_EMOJI, STARBOARD_COUNT

starboard_types = {0: "sonnet_starboard", "csv": [], "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT]]}


async def starboard_channel_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "starboard-channel", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


async def set_starboard_emoji(message, args, client, **kwargs):

    if args:
        emoji = args[0]
        with db_hlapi(message.guild.id) as database:
            database.add_config("starboard-emoji", emoji)
    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        emoji = mconf["starboard-emoji"]

    if kwargs["verbose"]: await message.channel.send(f"Updated starboard emoji to {emoji}")


async def set_starboard_use(message, args, client, **kwargs):

    if args:
        gate = parse_boolean(args[0])
        with db_hlapi(message.guild.id) as database:
            database.add_config("starboard-enabled", int(gate))
    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        gate = bool(int(mconf["starboard-enabled"]))

    if kwargs["verbose"]: await message.channel.send(f"Starboard set to {bool(gate)}")


async def set_starboard_count(message, args, client, **kwargs):

    if args:

        try:
            count = int(float(args[0]))

            with db_hlapi(message.guild.id) as database:
                database.add_config("starboard-count", count)

            if kwargs["verbose"]: await message.channel.send(f"Updated starboard count to {count}")

        except ValueError:
            await message.channel.send("Invalid input, please enter a number")

    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        count = mconf["starboard-count"]
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
    'starboard-enabled': {
        'pretty_name': 'starboard-enabled <bool>',
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

version_info = "1.1.6-DEV"
