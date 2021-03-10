# User update tracking
# Ultrabear 2021

import importlib

import discord
from datetime import datetime

import lib_loaders
importlib.reload(lib_loaders)
import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)

from lib_db_obfuscator import db_hlapi
from lib_loaders import inc_statistics


async def on_member_update(before, after, **kargs):

    client = kargs["client"]
    inc_statistics([before.guild.id, "on-member-update", kargs["kernel_ramfs"]])

    if before.nick == after.nick:
        return

    with db_hlapi(before.guild.id) as db:
        username_log = db.grab_config("username-log")

    if username_log and (log_channel := client.get_channel(int(username_log))):
        message_embed = discord.Embed(title=f"Username updated", color=0x008744)
        message_embed.set_author(name=f"{before} ({before.id})", icon_url=before.avatar_url)
        message_embed.add_field(name="Before", value=before.nick)
        message_embed.add_field(name="After", value=after.nick)
        message_embed.timestamp = datetime.utcnow()

        try:
            await log_channel.send(embed=message_embed)
        except discord.errors.Forbidden:
            pass


category_info = {'name': 'UserUpdate'}

commands = {
    "on-member-update": on_member_update,
    }

version_info = "1.1.5"
