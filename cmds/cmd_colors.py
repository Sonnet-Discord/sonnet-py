# Set colors of embeds dynamically
# Ultrabear 2021

import importlib

import discord

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_embed_color, embed_colors

from typing import Any, List
import lib_lexdpyk_h as lexdpyk


def zpadhex(indata: int) -> str:
    col = hex(indata)[2:]
    return (6 - len(col)) * "0" + col


async def set_embed_typec(message: discord.Message, args: List[str], typec: str, verbose: bool, ramfs: lexdpyk.ram_filesystem) -> int:

    if args:

        if args[0] == "reset":

            with db_hlapi(message.guild.id) as db:
                db.add_config(f"embed-color-{typec}", "")

            if verbose: await message.channel.send(f"Reset {typec}-color to its default value")

            return 0

        try:
            colint: int = int(args[0], 16)
        except ValueError:
            await message.channel.send("ERROR: Not a valid color")
            return 1
    else:
        with db_hlapi(message.guild.id) as db:
            colhex = db.grab_config(f"embed-color-{typec}")
        if colhex: await message.channel.send(f"{typec}-color is set to {zpadhex(int(colhex, 16))}")
        else: await message.channel.send(f"{typec}-color is not set (default: {zpadhex(load_embed_color(message.guild, typec, ramfs))})")

        return 0

    if colint >= (2**24):
        await message.channel.send("ERROR: Color out of 24bit range")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config(f"embed-color-{typec}", hex(colint))

    if verbose: await message.channel.send(f"Updated {typec}-color to {zpadhex(colint)}")

    return 0


async def set_embed_primary(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    return await set_embed_typec(message, args, embed_colors.primary, kwargs["verbose"], kwargs["ramfs"])


async def set_embed_creation(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    return await set_embed_typec(message, args, embed_colors.creation, kwargs["verbose"], kwargs["ramfs"])


async def set_embed_edit(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    return await set_embed_typec(message, args, embed_colors.edit, kwargs["verbose"], kwargs["ramfs"])


async def set_embed_deletion(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    return await set_embed_typec(message, args, embed_colors.deletion, kwargs["verbose"], kwargs["ramfs"])


category_info = {'name': 'colors', 'pretty_name': 'Colors', 'description': 'Configuration tool for sonnet embed colors'}

commands = {
    'set-colour-primary': {
        'alias': 'set-color-primary'
        },
    'set-color-primary':
        {
            'pretty_name': 'set-color-primary <hexcolor|"reset">',
            'description': 'Set primary embed color',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_embed_primary
            },
    'set-colour-creation': {
        'alias': 'set-color-creation'
        },
    'set-color-creation':
        {
            'pretty_name': 'set-color-creation <hexcolor|"reset">',
            'description': 'Set creation embed color',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_embed_creation
            },
    'set-colour-edit': {
        'alias': 'set-color-edit'
        },
    'set-color-edit': {
        'pretty_name': 'set-color-edit <hexcolor|"reset">',
        'description': 'Set edit embed color',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': set_embed_edit
        },
    'set-colour-deletion': {
        'alias': 'set-color-deletion'
        },
    'set-color-deletion':
        {
            'pretty_name': 'set-color-deletion <hexcolor|"reset">',
            'description': 'Set deletion embed color',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_embed_deletion
            },
    }

version_info: str = "1.2.4"
