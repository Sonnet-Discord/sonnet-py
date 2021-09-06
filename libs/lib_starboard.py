# Starboard deduplication library
# Stores shared functions and shared definitions for starboard
# This file SHOULD NOT be imported by any files other than starboard
# Ultrabear 2021

import importlib

import discord

import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_parsers

importlib.reload(lib_parsers)

from lib_parsers import generate_reply_field
from lib_sonnetconfig import STARBOARD_EMOJI, STARBOARD_COUNT

from typing import Dict, Union, Any

starboard_cache: Dict[Union[str, int], Any] = {
    0: "sonnet_starboard",
    "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT], ["starboard-channel", ""]]
    }


async def build_starboard_embed(message: discord.Message) -> discord.Embed:

    # Generate replies
    message_content = generate_reply_field(message)

    # Generate embed
    starboard_embed = discord.Embed(title="Starred message", description=message_content, color=0xffa700)

    for i in message.attachments:
        if any(i.url.endswith(ext) for ext in [".png", ".bmp", ".jpg", ".jpeg", ".gif", ".webp"]):
            starboard_embed.set_image(url=i.url)

    starboard_embed.set_author(name=str(message.author), icon_url=str(message.author.avatar_url))
    starboard_embed.timestamp = message.created_at
    starboard_embed.set_footer(text=f"#{message.channel}")

    return starboard_embed
