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
import lib_compatibility

importlib.reload(lib_compatibility)

from lib_parsers import generate_reply_field
from lib_sonnetconfig import STARBOARD_EMOJI, STARBOARD_COUNT, REGEX_VERSION
from lib_compatibility import user_avatar_url

from typing import Dict, Union, Any

# Import re here to trick type checker into using re stubs even if importlib grabs re2, they (should) have the same stubs
import re

# Place this in the globals scope by hand to avoid pyflakes saying its a redefinition
globals()["re"] = importlib.import_module(REGEX_VERSION)

_image_filetypes = [".png", ".bmp", ".jpg", ".jpeg", ".gif", ".webp"]
_url_chars = "[a-zA-Z0-9\.\-]"

# match https?://
# match optional newline
# match ([_url_chars]+/)+ accounts for multiple subdirectories with at least one
# match [_url_chars]*.(imageext) potential filename
_urlregex = re.compile(
    "(https?://)"  # https
    "(?:\n)?"  # newline
    f"((?:{_url_chars}+/)+"  # make subdirs group be non capturing to avoid extra captures
    f"{_url_chars}*\\.)({'|'.join(i[1:] for i in _image_filetypes)})"  # image filename
    )

starboard_cache: Dict[Union[str, int], Any] = {
    0: "sonnet_starboard",
    "text": [["starboard-enabled", "0"], ["starboard-emoji", STARBOARD_EMOJI], ["starboard-count", STARBOARD_COUNT], ["starboard-channel", ""]]
    }


async def build_starboard_embed(message: discord.Message) -> discord.Embed:

    # Generate replies
    message_content = generate_reply_field(message)

    # Generate embed
    starboard_embed = discord.Embed(title="Starred message", description=message_content, color=0xffa700)

    if link := _urlregex.match(message.content):
        starboard_embed.set_image(url=link.group())

    for i in message.attachments:
        if any(i.url.endswith(ext) for ext in _image_filetypes):
            starboard_embed.set_image(url=i.url)

    starboard_embed.set_author(name=str(message.author), icon_url=user_avatar_url(message.author))
    starboard_embed.timestamp = message.created_at
    starboard_embed.set_footer(text=f"#{message.channel}")

    return starboard_embed
