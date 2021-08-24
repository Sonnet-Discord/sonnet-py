# Handlers for reactions
# Ultrabear 2021

import importlib

import discord
import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, inc_statistics_better
from lib_parsers import generate_reply_field

from sonnet_cfg import STARBOARD_EMOJI, STARBOARD_COUNT

from typing import Dict, Any, Union

starboard_types: Dict[Union[str, int], Any] = {
    0: "sonnet_starboard",
    "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT], ["starboard-channel", ""]]
    }


async def on_reaction_add(reaction: discord.Reaction, user: discord.User, **kargs: Any) -> None:

    message = reaction.message

    # Skip if not a guild
    if not message.guild:
        return

    inc_statistics_better(message.guild.id, "on-reaction-add", kargs["kernel_ramfs"])
    mconf = load_message_config(message.guild.id, kargs["ramfs"], datatypes=starboard_types)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        if (channel_id := mconf["starboard-channel"]) and (channel := kargs["client"].get_channel(int(channel_id))):
            with db_hlapi(message.guild.id) as db:
                db.inject_enum("starboard", [
                    ("messageID", str),
                    ])
                if not (db.grab_enum("starboard", str(message.id))) and not (int(channel_id) == message.channel.id):

                    # Add to starboard
                    db.set_enum("starboard", [str(message.id)])

                    # Generate replies
                    message_content = generate_reply_field(message)

                    # Generate embed
                    starboard_embed = discord.Embed(title="Starred message", description=message_content, color=0xffa700)

                    for i in message.attachments:
                        if any([i.url.endswith(ext) for ext in [".png", ".bmp", ".jpg", ".jpeg", ".gif", ".webp"]]):
                            starboard_embed.set_image(url=i.url)

                    starboard_embed.set_author(name=str(message.author), icon_url=str(message.author.avatar_url))
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

version_info: str = "pre2.0.0-DEV"
