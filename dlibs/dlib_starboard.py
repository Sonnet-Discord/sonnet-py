# Handlers for reactions
# Ultrabear 2021

import importlib

import discord, asyncio
from datetime import datetime

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, inc_statistics
from lib_parsers import ifgate, generate_reply_field

from sonnet_cfg import STARBOARD_EMOJI, STARBOARD_COUNT

starboard_types = {0: "sonnet_starboard", "csv": [], "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT]]}


async def on_reaction_add(reaction, user, **kargs):

    # Skip if not a guild
    if not reaction.message.guild:
        return

    message = reaction.message

    inc_statistics([message.guild.id, "on-reaction-add", kargs["kernel_ramfs"]])
    mconf = load_message_config(message.guild.id, kargs["ramfs"], datatypes=starboard_types)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        with db_hlapi(message.guild.id) as db:
            if channel_id := db.grab_config("starboard-channel"):
                if bool(channel := kargs["client"].get_channel(int(channel_id))
                        ) and not (db.in_starboard(message.id)) and not (int(channel_id) == message.channel.id) and db.add_to_starboard(message.id):

                    # Generate replies
                    message_content = generate_reply_field(message)

                    # Generate embed
                    starboard_embed = discord.Embed(title="Starred message", description=message_content, color=0xffa700)

                    for i in message.attachments:
                        if ifgate([i.url.endswith(ext) for ext in [".png", ".bmp", ".jpg", ".jpeg", ".gif", ".webp"]]):
                            starboard_embed.set_image(url=i.url)

                    starboard_embed.set_author(name=message.author, icon_url=message.author.avatar_url)
                    starboard_embed.timestamp = message.created_at
                    starboard_embed.set_footer(text=f"#{message.channel}")

                    try:
                        await channel.send(embed=starboard_embed)
                    except discord.errors.Forbidden:
                        pass


category_info = {'name': 'Starboard'}

commands = {
    "on-reaction-add": on_reaction_add,
    }

version_info = "1.1.6"
