# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import importlib

import discord, time, asyncio
from datetime import datetime

import lib_db_obfuscator; importlib.reload(lib_db_obfuscator)
import lib_parsers; importlib.reload(lib_parsers)
import lib_loaders; importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, directBinNumber
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions


async def on_message_delete(message, **kargs):

    client = kargs["client"]
    # Ignore bots
    if parse_skip_message(client, message):
        return

    # Add to log
    with db_hlapi(message.guild.id) as db:
       message_log = db.grab_config("message-log")
    if message_log:
        message_log = client.get_channel(int(message_log))
        if message_log:
            message_embed = discord.Embed(title=f"Message deleted in #{message.channel}", description=message.content, color=0xd62d20)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcnow()

            await message_log.send(embed=message_embed)


async def on_message_edit(old_message, message, **kargs):

    client = kargs["client"]
    ramfs = kargs["ramfs"]

    # Ignore bots
    if parse_skip_message(client, message):
        return

    # Add to log
    with db_hlapi(message.guild.id) as db:
       message_log = db.grab_config("message-log")
    if message_log:
        message_log = client.get_channel(int(message_log))
        if message_log:
            message_embed = discord.Embed(title=f"Message edited in #{message.channel}", color=0xffa700)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)

            old_msg = (old_message.content or "NULL")
            message_embed.add_field(name="Old Message", value=(old_msg)[:1024], inline=False)
            if len(old_msg) > 1024:
                message_embed.add_field(name="(Continued)", value=(old_msg)[1024:], inline=False)

            msg = (message.content or "NULL")
            message_embed.add_field(name="New Message", value=(msg)[:1024], inline=False)
            if len(msg) > 1024:
                message_embed.add_field(name="(Continued)", value=(msg)[1024:], inline=False)

            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcfromtimestamp(int(time.time()))
            await message_log.send(embed=message_embed)

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, infraction_type = await parse_blacklist(message, mconf)

    if broke_blacklist:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        stats = {}
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client)


async def antispam_check(guildid, userid, ramfs, **kargs):
    messagecount = kargs["messages"]
    timecount = kargs["time"]*1000
    try:
        messages = ramfs.read_f(f"antispam/{guildid}.cache.asam")
        messages.seek(0)
        droptime = round(time.time()*1000) - timecount
        userlist = []
        ismute = 1

        while a := messages.read(16):
            uid = int.from_bytes(a[:8], "little")
            mtime = int.from_bytes(a[8:], "little")
            if mtime > droptime:
                userlist.append([uid, mtime])
                if uid == userid:
                    ismute += 1

        userlist.append([userid, round(time.time()*1000)])
        messages.seek(0)
        for i in userlist:
            messages.write(bytes(directBinNumber(i[0], 8) + directBinNumber(i[1], 8)))
        messages.truncate()
        if ismute > messagecount:
            return True
        else:
            return False

    except FileNotFoundError:
        messages = ramfs.create_f(f"antispam/{guildid}.cache.asam")
        messages.write(bytes(directBinNumber(userid, 8) + directBinNumber(round(time.time()*1000), 8)))
        return False


async def on_message(message, **kargs):

    client = kargs["client"]
    ramfs = kargs["ramfs"]
    main_version_info = kargs["kernel_version"]
    bot_start_time = kargs["bot_start"]
    command_modules, command_modules_dict = kargs["command_modules"]

    # Statistics.
    stats = {"start": round(time.time() * 100000), "end": 0}

    if parse_skip_message(client, message):
        return

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against blacklist
    stats["start-automod"] = round(time.time() * 100000)
    blacklist_dump = asyncio.create_task(parse_blacklist(message, mconf))
    spammer = asyncio.create_task(antispam_check(message.channel.guild.id, message.author.id, ramfs, messages=3, time=2))

    # If blacklist broken generate infraction
    broke_blacklist, infraction_type = await blacklist_dump
    if broke_blacklist:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client)

    if await spammer:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        with db_hlapi(message.guild.id) as db:
            if not db.is_muted(userid=message.author.id):
                await command_modules_dict["mute"]['execute'](message, ["20s", int(message.author.id), "[AUTOMOD]",  "Antispam"], client)

    stats["end-automod"] = round(time.time() * 100000)

    # Check if this is meant for us.
    if not message.content.startswith(mconf["prefix"]):
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][len(mconf["prefix"]):]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict.keys():
        permission = await parse_permissions(message, command_modules_dict[command]['permission'])
        try:
            if permission:
                stats["end"] = round(time.time() * 100000)
                await command_modules_dict[command]['execute'](message, arguments, client, stats=stats, cmds=command_modules, ramfs=ramfs, bot_start=bot_start_time, dlibs=kargs["dynamiclib_modules"][0], main_version=main_version_info)
                # Regenerate cache
                if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
                    ramfs.remove_f(f"datastore/{message.guild.id}.cache.db")
                    if command_modules_dict[command]['cache'] == "regenerate":
                        load_message_config(message.guild.id, ramfs)
        except discord.errors.Forbidden:
            pass # Nothing we can do if we lack perms to speak


category_info = {
    'name': 'Messages'
}


commands = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    }


version_info = "1.1.0-DEV"
