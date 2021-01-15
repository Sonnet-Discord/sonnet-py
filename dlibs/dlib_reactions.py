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
from lib_parsers import ifgate


async def on_reaction_add(reaction, user, **kargs):

    # Skip if not a guild
    if not reaction.message.guild:
        return

    inc_statistics([reaction.message.guild.id, "on-reaction-add", kargs["kernel_ramfs"]])
    mconf = load_message_config(reaction.message.guild.id, kargs["ramfs"])

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        with db_hlapi(reaction.message.guild.id) as db:
            if channel_id := db.grab_config("starboard-channel"):
                if bool(channel := kargs["client"].get_channel(int(channel_id))) and not (db.in_starboard(reaction.message.id)) and not (int(channel_id) == reaction.message.channel.id):

                    db.add_to_starboard(reaction.message.id)

                    jump = f"\n\n[(Link)]({reaction.message.jump_url})"
                    starboard_embed = discord.Embed(title="Starred message", description=reaction.message.content[:2048 - len(jump)] + jump, color=0xffa700)

                    for i in reaction.message.attachments:
                        if ifgate([i.url.endswith(ext) for ext in [".png", ".bmp", ".jpg", ".jpeg"]]):
                            starboard_embed.set_image(url=i.url)

                    starboard_embed.set_author(name=reaction.message.author, icon_url=reaction.message.author.avatar_url)
                    starboard_embed.timestamp = reaction.message.created_at

                    await channel.send(embed=starboard_embed)


async def on_raw_reaction_add(payload, **kargs):
    inc_statistics([payload.guild_id, "on-raw-reaction-add", kargs["kernel_ramfs"]])
    message = await kargs["client"].get_channel(payload.channel_id).fetch_message(payload.message_id)
    reaction = [i for i in message.reactions if str(i) == str(payload.emoji)][0]
    await asyncio.sleep(0.05)  # Wait 50ms to not overload db
    await on_reaction_add(reaction, payload.user_id, client=kargs["client"], ramfs=kargs["ramfs"], kernel_ramfs=kargs["kernel_ramfs"])


category_info = {'name': 'Reactions'}

commands = {
    "on-raw-reaction-add": on_raw_reaction_add,
    "on-reaction-add": on_reaction_add,
    }

version_info = "1.1.1-DEV"
