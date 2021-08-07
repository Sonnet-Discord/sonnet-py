# Starboard system
# Ultrabear 2020

import importlib

import discord

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

from typing import List, Dict, Any, Union

starboard_types: Dict[Union[str, int], Any] = {
    0: "sonnet_starboard",
    "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT], ["starboard-channel", ""]]
    }


async def starboard_channel_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "starboard-channel", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def set_starboard_emoji(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    if args:
        emoji = args[0]
        with db_hlapi(message.guild.id) as database:
            database.add_config("starboard-emoji", emoji)
            if kwargs["verbose"]: await message.channel.send(f"Updated starboard emoji to {emoji}")
    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        emoji = mconf["starboard-emoji"]
        await message.channel.send(f"Starboard emoji is {emoji}")


async def set_starboard_use(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    if args:
        gate = parse_boolean(args[0])
        with db_hlapi(message.guild.id) as database:
            database.add_config("starboard-enabled", str(int(gate)))
            if kwargs["verbose"]: await message.channel.send(f"Set starboard enabled to {bool(gate)}")
    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        gate = bool(int(mconf["starboard-enabled"]))
        await message.channel.send(f"Starboard enabled is {bool(gate)}")


async def set_starboard_count(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    if args:

        try:
            count = int(args[0])

            if count > 100:
                await message.channel.send("ERROR: Cannot set a starboard count higher than 100")
                return 1

            with db_hlapi(message.guild.id) as database:
                database.add_config("starboard-count", str(int(count)))

            if kwargs["verbose"]: await message.channel.send(f"Updated starboard count to {count}")

        except ValueError:
            await message.channel.send("ERROR: Invalid input, enter a number")
            return 1

    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_types)
        count = int(mconf["starboard-count"])
        await message.channel.send(f"Starboard count is {count}")


category_info: Dict[str, str] = {'name': 'starboard', 'pretty_name': 'Starboard', 'description': 'Starboard commands.'}

commands: Dict[str, Dict[str, Any]] = {
    'starboard-channel':
        {
            'pretty_name': 'starboard-channel <channel>',
            'description': 'Change Starboard channel',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_starboard',
            'execute': starboard_channel_change
            },
    'starboard-emoji':
        {
            'pretty_name': 'starboard-emoji <emoji>',
            'description': 'Set the starboard emoji',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_starboard',
            'execute': set_starboard_emoji
            },
    'starboard-enabled':
        {
            'pretty_name': 'starboard-enabled <bool>',
            'description': 'Toggle starboard on or off',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_starboard',
            'execute': set_starboard_use
            },
    'starboard-count':
        {
            'pretty_name': 'starboard-count <number>',
            'description': 'Set starboard reaction count threshold',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_starboard',
            'execute': set_starboard_count
            }
    }

version_info: str = "pre2.0.0-DEV"
