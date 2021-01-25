# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import importlib

import time, asyncio, os, threading, hashlib
from datetime import datetime

import discord, lz4.frame

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_parsers
importlib.reload(lib_parsers)
import lib_loaders
importlib.reload(lib_loaders)
import lib_encryption_wrapper
importlib.reload(lib_encryption_wrapper)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, directBinNumber, inc_statistics
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions, grab_files
from lib_encryption_wrapper import encrypted_writer


async def catch_logging_error(channel, contents, files):
    try:
        if files:
            await channel.send(embed=contents, files=files)
        else:
            await channel.send(embed=contents)
    except discord.errors.Forbidden:
        pass
    except discord.errors.HTTPException:
        try:
            if files:
                await channel.send("There were files attached but they exceeeded the guild filesize limit", embed=contents)
        except discord.errors.Forbidden:
            pass


async def on_message_delete(message, **kargs):

    if kargs["kernel_version"] != "1.1.0 'LeXdPyK'":
        files = grab_files(message.channel.guild.id, message.id, kargs["kernel_ramfs"], delete=True)
    else:
        files = None

    client = kargs["client"]
    # Ignore bots
    if parse_skip_message(client, message):
        return

    inc_statistics([message.guild.id, "on-message-delete", kargs["kernel_ramfs"]])

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

            await catch_logging_error(message_log, message_embed, files)


async def attempt_message_delete(message):
    try:
        await message.delete()
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def on_message_edit(old_message, message, **kargs):

    client = kargs["client"]
    ramfs = kargs["ramfs"]

    # Ignore bots
    if parse_skip_message(client, message):
        return

    inc_statistics([message.guild.id, "on-message-edit", kargs["kernel_ramfs"]])

    # Add to log
    with db_hlapi(message.guild.id) as db:
        message_log = db.grab_config("message-log")

    # Skip logging if message is the same or mlog doesnt exist
    if message_log and not (old_message.content == message.content):
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
            asyncio.create_task(catch_logging_error(message_log, message_embed, None))

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, infraction_type = parse_blacklist([message, mconf])

    if broke_blacklist:
        asyncio.create_task(attempt_message_delete(message))
        await kargs["command_modules"][1][mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client)


def antispam_check(indata):

    guildid, userid, msend, ramfs, messagecount, timecount = indata

    messagecount = int(messagecount)
    timecount = int(timecount) * 1000

    try:
        messages = ramfs.read_f(f"antispam/{guildid}.cache.asam")
        messages.seek(0)
        droptime = round(time.time() * 1000) - timecount
        userlist = []
        ismute = 1

        # Parse though all messages, drop them if they are old, and add them to spamlist if uids match
        while a := messages.read(16):
            uid = int.from_bytes(a[:8], "little")
            mtime = int.from_bytes(a[8:], "little")
            if mtime > droptime:
                userlist.append([uid, mtime])
                if uid == userid:
                    ismute += 1

        # I barely write code comments but this unholy sin converts a datetime object to normal UTC
        sent_at = (msend - datetime(1970, 1, 1)).total_seconds()

        userlist.append([userid, round(sent_at * 1000)])
        messages.seek(0)
        for i in userlist:
            messages.write(bytes(directBinNumber(i[0], 8) + directBinNumber(i[1], 8)))
        messages.truncate()
        if ismute >= messagecount:
            return True
        else:
            return False

    except FileNotFoundError:
        messages = ramfs.create_f(f"antispam/{guildid}.cache.asam")
        messages.write(bytes(directBinNumber(userid, 8) + directBinNumber(round(time.time() * 1000), 8)))
        return False


async def download_file(nfile, compression, encryption, filename, ramfs, mgid):

    await nfile.save(compression, seek_begin=False)
    compression.close()
    encryption.close()

    await asyncio.sleep(60 * 30)

    try:
        os.remove(filename)
    except FileNotFoundError:
        pass
    try:
        ramfs.rmdir(f"files/{mgid[0]}/{mgid[1]}")
    except FileNotFoundError:
        pass


def download_single_file(contents):

    discord_file, filename, key, iv, ramfs, mgid = contents

    encryption_fileobj = encrypted_writer(filename, key, iv)

    compression_fileobj = lz4.frame.LZ4FrameFile(filename=encryption_fileobj, mode="wb")

    asyncio.create_task(download_file(discord_file, compression_fileobj, encryption_fileobj, filename, ramfs, mgid))


async def log_message_files(message, kernel_ramfs):

    for i in message.attachments:

        ramfs_path = f"files/{message.channel.guild.id}/{message.id}/{i.filename}"

        keyfile = kernel_ramfs.create_f(f"{ramfs_path}/key")
        keyfile.write(key := os.urandom(32))
        keyfile.write(iv := os.urandom(16))

        pointerfile = kernel_ramfs.create_f(f"{ramfs_path}/pointer")
        pointer = hashlib.sha256(i.filename.encode("utf8") + key + iv).hexdigest()
        file_loc = f"./datastore/{message.channel.guild.id}-{pointer}.cache.db"
        pointerfile.write(file_loc.encode("utf8"))

        threading.Thread(target=download_single_file, args=([i, file_loc, key, iv, kernel_ramfs, [message.channel.guild.id, message.id]], )).run()


async def on_message(message, **kargs):

    client = kargs["client"]
    ramfs = kargs["ramfs"]
    main_version_info = kargs["kernel_version"]
    bot_start_time = kargs["bot_start"]
    command_modules, command_modules_dict = kargs["command_modules"]

    # Statistics.
    stats = {"start": round(time.time() * 100000)}

    if parse_skip_message(client, message):
        return

    inc_statistics([message.guild.id, "on-message", kargs["kernel_ramfs"]])

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against automod
    stats["start-automod"] = round(time.time() * 100000)

    spammer = antispam_check([message.channel.guild.id, message.author.id, message.created_at, ramfs, mconf["antispam"][0], mconf["antispam"][1]])

    message_deleted = False

    # If blacklist broken generate infraction
    broke_blacklist, infraction_type = parse_blacklist([message, mconf])
    if broke_blacklist:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        asyncio.create_task(command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client))

    if spammer:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        with db_hlapi(message.guild.id) as db:
            if not db.is_muted(userid=message.author.id):
                asyncio.create_task(command_modules_dict["mute"]['execute'](message, [int(message.author.id), "20s", "[AUTOMOD]", "Antispam"], client))

    stats["end-automod"] = round(time.time() * 100000)

    # Log files if not deleted
    if not message_deleted:
        asyncio.create_task(log_message_files(message, kargs["kernel_ramfs"]))

    # Check if this is meant for us.
    if not message.content.startswith(mconf["prefix"]):
        if client.user.mentioned_in(message) and str(client.user.id) in message.content:
            await message.channel.send(f"My prefix for this guild is {mconf['prefix']}")
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

                await command_modules_dict[command]['execute'](
                    message,
                    arguments,
                    client,
                    stats=stats,
                    cmds=command_modules,
                    ramfs=ramfs,
                    bot_start=bot_start_time,
                    dlibs=kargs["dynamiclib_modules"][0],
                    main_version=main_version_info,
                    kernel_ramfs=kargs["kernel_ramfs"]
                    )

                # Regenerate cache
                if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
                    ramfs.remove_f(f"datastore/{message.guild.id}.cache.db")
                    if command_modules_dict[command]['cache'] == "regenerate":
                        load_message_config(message.guild.id, ramfs)
        except discord.errors.Forbidden:
            pass  # Nothing we can do if we lack perms to speak


category_info = {'name': 'Messages'}

commands = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    }

version_info = "1.1.2-DEV"
