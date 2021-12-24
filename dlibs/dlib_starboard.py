# Handlers for reactions
# Ultrabear 2021

import importlib

import discord
import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)
import lib_starboard

importlib.reload(lib_starboard)

from lib_starboard import starboard_cache, build_starboard_embed
from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, inc_statistics_better

from typing import Any
import lib_lexdpyk_h as lexdpyk


async def on_reaction_add(reaction: discord.Reaction, user: discord.User, **kargs: Any) -> None:

    client: discord.Client = kargs["client"]
    kernel_ramfs: lexdpyk.ram_filesystem = kargs["kernel_ramfs"]
    ramfs: lexdpyk.ram_filesystem = kargs["ramfs"]

    message = reaction.message

    # Skip if not a guild
    if not message.guild:
        return

    inc_statistics_better(message.guild.id, "on-reaction-add", kernel_ramfs)
    mconf = load_message_config(message.guild.id, ramfs, datatypes=starboard_cache)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        if (channel_id := mconf["starboard-channel"]) and (channel := client.get_channel(int(channel_id))) and isinstance(channel, discord.TextChannel):

            with db_hlapi(message.guild.id) as db:
                db.inject_enum("starboard", [
                    ("messageID", str),
                    ])
                with db.enum_context("starboard") as starboard:
                    if not (starboard.grab(str(message.id))) and not (int(channel_id) == message.channel.id):

                        # Add to starboard
                        starboard.set([str(message.id)])

                        try:
                            await channel.send(embed=(await build_starboard_embed(message)))
                        except discord.errors.Forbidden:
                            pass


category_info = {'name': 'Starboard'}

commands = {
    "on-reaction-add": on_reaction_add,
    }

version_info: str = "1.2.11-DEV"
