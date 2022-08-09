# Starboard system
# Ultrabear 2020

import importlib

import discord

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_constants

importlib.reload(lib_constants)
import lib_loaders

importlib.reload(lib_loaders)
import lib_starboard

importlib.reload(lib_starboard)

from lib_starboard import starboard_cache, build_starboard_embed
from lib_parsers import parse_boolean_strict, update_log_channel, parse_channel_message
from lib_loaders import load_message_config
from lib_db_obfuscator import db_hlapi
import lib_constants as constants

from typing import List, Dict, Any


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
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_cache)
        emoji = mconf["starboard-emoji"]
        await message.channel.send(f"Starboard emoji is {emoji}")


async def set_starboard_use(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    if args:
        gate = parse_boolean_strict(args[0])

        if gate is None:
            await message.channel.send("ERROR: Could not parse bool value")
            return 1

        with db_hlapi(message.guild.id) as database:
            database.add_config("starboard-enabled", str(int(gate)))
            if kwargs["verbose"]: await message.channel.send(f"Set starboard enabled to {gate}")
    else:
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_cache)
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
        mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_cache)
        count = int(mconf["starboard-count"])
        await message.channel.send(f"Starboard count is {count}")


async def force_starboard(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    mconf = load_message_config(message.guild.id, kwargs["ramfs"], datatypes=starboard_cache)

    try:
        starmessage, _ = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    if (channel_id := mconf["starboard-channel"]) and (channel := client.get_channel(int(channel_id))):

        if not isinstance(channel, discord.TextChannel):
            await message.channel.send("ERROR: Starboard channel is not a TextChannel")
            return 1

        with db_hlapi(message.guild.id) as db:
            db.inject_enum("starboard", [
                ("messageID", str),
                ])

            # Add to starboard
            db.set_enum("starboard", [str(starmessage.id)])

        try:
            await channel.send(embed=(await build_starboard_embed(starmessage)))
        except discord.errors.Forbidden:
            await message.channel.send(constants.sonnet.error_embed)
            return 1

    else:
        await message.channel.send("ERROR: No starboard channel")
        return 1


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
            },
    'starboard-forceboard':
        {
            'pretty_name': 'starboard-forceboard <message>',
            'description': 'Forcibly starboard a message and add it to the starboard db',
            'permission': 'administrator',
            'cache': 'keep',
            'execute': force_starboard
            },
    }

version_info: str = "1.2.14-DEV"
