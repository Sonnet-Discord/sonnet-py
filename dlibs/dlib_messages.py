# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import importlib

import time, asyncio, os, hashlib
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
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)
import lib_constants

importlib.reload(lib_constants)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, inc_statistics_better, read_vnum, write_vnum, load_embed_color, embed_colors
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions, grab_files, generate_reply_field
from lib_encryption_wrapper import encrypted_writer

from typing import List, Any, Dict, Optional, Callable, Tuple, Coroutine
import lib_lexdpyk_h as lexdpyk
import lib_constants as constants


async def catch_logging_error(channel: discord.TextChannel, contents: str, files: Optional[List[discord.File]]) -> None:
    try:
        await channel.send(embed=contents, files=files)
    except discord.errors.Forbidden:
        pass
    except discord.errors.HTTPException:
        try:
            if files:
                await channel.send("There were files attached but they exceeded the guild filesize limit", embed=contents)
        except discord.errors.Forbidden:
            pass


async def on_message_delete(message: discord.Message, **kargs: Any) -> None:

    client: discord.Client = kargs["client"]
    # Ignore bots
    if parse_skip_message(client, message):
        return

    files: Optional[List[discord.File]] = grab_files(message.guild.id, message.id, kargs["kernel_ramfs"], delete=True)

    inc_statistics_better(message.guild.id, "on-message-delete", kargs["kernel_ramfs"])

    # Add to log
    with db_hlapi(message.guild.id) as db:
        message_log = db.grab_config("message-log")

    if message_log and (log_channel := client.get_channel(int(message_log))):

        message_embed = discord.Embed(
            title=f"Message deleted in #{message.channel}", description=message.content[:constants.embed.description], color=load_embed_color(message.guild, embed_colors.deletion, kargs["ramfs"])
            )
        message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)

        if (r := message.reference) and (rr := r.resolved):
            message_embed.add_field(name="Replying to:", value=f"{rr.author.mention} [(Link)]({rr.jump_url})")

        message_embed.set_footer(text=f"Message ID: {message.id}")
        message_embed.timestamp = message.created_at

        await catch_logging_error(log_channel, message_embed, files)


async def attempt_message_delete(message: discord.Message) -> None:
    try:
        await message.delete()
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def grab_an_adult(discord_message: discord.Message, client: discord.Client, mconf: Dict[str, Any], ramfs: lexdpyk.ram_filesystem) -> None:

    if mconf["regex-notifier-log"] and (notify_log := client.get_channel(int(mconf["regex-notifier-log"]))):

        message_content = generate_reply_field(discord_message)

        # Message has been grabbed, start generating embed
        message_embed = discord.Embed(
            title=f"Auto Flagged Message in #{discord_message.channel}", description=message_content, color=load_embed_color(discord_message.guild, embed_colors.primary, ramfs)
            )

        message_embed.set_author(name=discord_message.author, icon_url=discord_message.author.avatar_url)
        message_embed.timestamp = discord_message.created_at

        # Grab files async
        awaitobjs = [asyncio.create_task(i.to_file()) for i in discord_message.attachments]
        fileobjs = [await i for i in awaitobjs]

        await catch_logging_error(notify_log, message_embed, fileobjs)


async def on_message_edit(old_message: discord.Message, message: discord.Message, **kargs: Any) -> None:

    client: discord.Client = kargs["client"]
    ramfs: lexdpyk.ram_filesystem = kargs["ramfs"]
    kernel_ramfs: lexdpyk.ram_filesystem = kargs["kernel_ramfs"]

    # Ignore bots
    if parse_skip_message(client, message):
        return

    inc_statistics_better(message.guild.id, "on-message-edit", kernel_ramfs)

    # Add to log
    with db_hlapi(message.guild.id) as db:
        message_log = db.grab_config("message-edit-log") or db.grab_config("message-log")

    # Skip logging if message is the same or mlog doesnt exist
    if message_log and not (old_message.content == message.content):
        if message_log := client.get_channel(int(message_log)):

            lim: int = constants.embed.field.value

            message_embed = discord.Embed(title=f"Message edited in #{message.channel}", color=load_embed_color(message.guild, embed_colors.edit, ramfs))
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)

            old_msg = (old_message.content or "NULL")
            message_embed.add_field(name="Old Message", value=(old_msg)[:lim], inline=False)
            if len(old_msg) > lim:
                message_embed.add_field(name="(Continued)", value=(old_msg)[lim:lim * 2], inline=False)

            msg = (message.content or "NULL")
            message_embed.add_field(name="New Message", value=(msg)[:lim], inline=False)
            if len(msg) > lim:
                message_embed.add_field(name="(Continued)", value=(msg)[lim:lim * 2], inline=False)

            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcnow()
            asyncio.create_task(catch_logging_error(message_log, message_embed, None))

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, notify, infraction_type = parse_blacklist((message, mconf, ramfs), )

    if broke_blacklist:
        asyncio.create_task(attempt_message_delete(message))
        execargs = [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"]
        await kargs["command_modules"][1][mconf["blacklist-action"]]['execute'](message, execargs, client, verbose=False, ramfs=ramfs)

    if notify:
        asyncio.create_task(grab_an_adult(message, client, mconf, kargs["ramfs"]))


def antispam_check(message: discord.Message, ramfs: lexdpyk.ram_filesystem, antispam: List[str], charantispam: List[str]) -> Tuple[bool, str]:

    userid = message.author.id

    # Base antispam
    try:

        messagecount = int(antispam[0])
        timecount = int(float(antispam[1]) * 1000)

        messages = ramfs.read_f(f"{message.guild.id}/asam")
        messages.seek(0, 2)
        EOF = messages.tell()
        messages.seek(0)
        droptime = round(datetime.utcnow().timestamp() * 1000) - timecount
        userlist = []
        ismute = 1

        # Parse though all messages, drop them if they are old, and add them to spamlist if uids match
        while EOF > messages.tell():
            uid, mtime = [read_vnum(messages) for i in range(2)]
            if mtime > droptime:
                userlist.append([uid, mtime])
                if uid == userid:
                    ismute += 1

        sent_at: float = message.created_at.timestamp()

        userlist.append([userid, round(sent_at * 1000)])
        messages.seek(0)
        for i in userlist:
            for v in i:
                write_vnum(messages, v)
        messages.truncate()

        if ismute >= messagecount:
            return (True, "Antispam")

    except FileNotFoundError:
        messages = ramfs.create_f(f"{message.guild.id}/asam")
        write_vnum(messages, message.author.id)
        write_vnum(messages, round(1000 * message.created_at.timestamp()))

    # Char antispam
    try:

        messagecount = int(charantispam[0])
        timecount = int(float(charantispam[1]) * 1000)
        charcount = int(charantispam[2])

        messages = ramfs.read_f(f"{message.guild.id}/casam")
        messages.seek(0, 2)
        EOF = messages.tell()
        messages.seek(0)
        droptime = round(datetime.utcnow().timestamp() * 1000) - timecount
        userlist = []
        ismute = 1
        charc = 0

        # Parse though all messages, drop them if they are old, and add them to spamlist if uids match
        while EOF > messages.tell():
            uid, mtime, clen = [read_vnum(messages) for i in range(3)]
            if mtime > droptime:
                userlist.append([uid, mtime, clen])
                if uid == userid:
                    charc += clen
                    ismute += 1

        sent_at = message.created_at.timestamp()

        userlist.append([userid, round(sent_at * 1000), len(message.content)])
        messages.seek(0)
        for i in userlist:
            for v in i:
                write_vnum(messages, v)
        messages.truncate()

        if ismute >= messagecount and charc >= charcount:
            return (True, "CharAntispam")

    except FileNotFoundError:
        messages = ramfs.create_f(f"{message.guild.id}/casam")
        write_vnum(messages, message.author.id)
        write_vnum(messages, round(1000 * message.created_at.timestamp()))
        write_vnum(messages, len(message.content))

    return (False, "")


async def download_file(nfile: discord.File, compression: Any, encryption: Any, filename: str, ramfs: lexdpyk.ram_filesystem, mgid: List[int]) -> None:

    await nfile.save(compression, seek_begin=False)
    compression.close()
    encryption.close()

    await asyncio.sleep(60 * 30)

    try:
        os.remove(filename)
    except FileNotFoundError:
        pass
    try:
        ramfs.rmdir(f"{mgid[0]}/files/{mgid[1]}")
    except FileNotFoundError:
        pass


def download_single_file(discord_file: discord.File, filename: str, key: bytes, iv: bytes, ramfs: lexdpyk.ram_filesystem, mgid: List[int]) -> None:

    encryption_fileobj = encrypted_writer(filename, key, iv)

    compression_fileobj = lz4.frame.LZ4FrameFile(filename=encryption_fileobj, mode="wb")

    asyncio.create_task(download_file(discord_file, compression_fileobj, encryption_fileobj, filename, ramfs, mgid))


async def log_message_files(message: discord.Message, kernel_ramfs: lexdpyk.ram_filesystem) -> None:

    for i in message.attachments:

        fname: bytes = i.filename.encode("utf8")

        ramfs_path = f"{message.guild.id}/files/{message.id}/{hashlib.sha256(fname).hexdigest()}"

        namefile = kernel_ramfs.create_f(f"{ramfs_path}/name")
        namefile.write(fname)

        keyfile = kernel_ramfs.create_f(f"{ramfs_path}/key")
        keyfile.write(key := os.urandom(32))
        keyfile.write(iv := os.urandom(16))

        pointerfile = kernel_ramfs.create_f(f"{ramfs_path}/pointer")
        pointer = hashlib.sha256(fname + key + iv).hexdigest()
        file_loc = f"./datastore/{message.channel.guild.id}-{pointer}.cache.db"
        pointerfile.write(file_loc.encode("utf8"))

        download_single_file(i, file_loc, key, iv, kernel_ramfs, [message.channel.guild.id, message.id])


async def on_message(message: discord.Message, **kargs: Any) -> None:

    client: discord.Client = kargs["client"]
    ramfs: lexdpyk.ram_filesystem = kargs["ramfs"]
    kernel_ramfs: lexdpyk.ram_filesystem = kargs["kernel_ramfs"]
    main_version_info: str = kargs["kernel_version"]
    bot_start_time: float = kargs["bot_start"]

    command_modules: List[lexdpyk.cmd_module]
    command_modules_dict: lexdpyk.cmd_modules_dict

    command_modules, command_modules_dict = kargs["command_modules"]

    # Statistics.
    stats: Dict[str, int] = {"start": round(time.time() * 100000)}

    if parse_skip_message(client, message):
        return

    inc_statistics_better(message.guild.id, "on-message", kernel_ramfs)

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against automod
    stats["start-automod"] = round(time.time() * 100000)

    spammer, spamstr = antispam_check(message, ramfs, mconf["antispam"], mconf["char-antispam"])

    message_deleted: bool = False

    # If blacklist broken generate infraction
    broke_blacklist, notify, infraction_type = parse_blacklist((message, mconf, ramfs), )
    if broke_blacklist:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        execargs = [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"]
        asyncio.create_task(command_modules_dict[mconf["blacklist-action"]]['execute'](message, execargs, client, verbose=False, ramfs=ramfs))

    if spammer:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        with db_hlapi(message.guild.id) as db:
            if not db.is_muted(userid=message.author.id):
                execargs = [int(message.author.id), mconf["antispam-time"], "[AUTOMOD]", spamstr]
                asyncio.create_task(command_modules_dict["mute"]['execute'](message, execargs, client, verbose=False, ramfs=ramfs))

    if notify:
        asyncio.create_task(grab_an_adult(message, client, mconf, ramfs))

    stats["end-automod"] = round(time.time() * 100000)

    # Log files if not deleted
    if not message_deleted:
        asyncio.create_task(log_message_files(message, kernel_ramfs))

    # Check if this is meant for us.
    if not (message.content.startswith(mconf["prefix"])) or message_deleted:
        if client.user.mentioned_in(message) and str(client.user.id) in message.content:
            try:
                await message.channel.send(f"My prefix for this guild is {mconf['prefix']}")
            except discord.errors.Forbidden:
                pass  # Nothing we can do if we lack perms to speak
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][len(mconf["prefix"]):]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict.keys():
        if "alias" in command_modules_dict[command].keys():
            command = command_modules_dict[command]["alias"]
        permission = await parse_permissions(message, mconf, command_modules_dict[command]['permission'])
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
                    kernel_ramfs=kargs["kernel_ramfs"],
                    conf_cache=mconf,
                    verbose=True,
                    cmds_dict=command_modules_dict
                    )

                # Regenerate cache
                if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
                    for i in ["caches", "regex"]:
                        try:
                            ramfs.rmdir(f"{message.guild.id}/{i}")
                        except FileNotFoundError:
                            pass

                elif command_modules_dict[command]['cache'].startswith("direct:"):
                    for i in command_modules_dict[command]['cache'][len('direct:'):].split(";"):
                        try:
                            if i.startswith("(d)"):
                                ramfs.rmdir(f"{message.guild.id}/{i[3:]}")
                            elif i.startswith("(f)"):
                                ramfs.remove_f(f"{message.guild.id}/{i[3:]}")
                            else:
                                raise RuntimeError("Cache directive is invalid")
                        except FileNotFoundError:
                            pass

        except discord.errors.Forbidden as e:

            try:
                await message.channel.send(f"ERROR: Encountered a uncaught permission error while processing {command}")
                terr = True
            except discord.errors.Forbidden:
                terr = False  # Nothing we can do if we lack perms to speak

            if terr:  # If the error was not caused by message send perms then raise
                raise e

        except Exception as e:
            try:
                await message.channel.send(f"FATAL ERROR: uncaught exception while processing {command}")
            except discord.errors.Forbidden:
                pass
            raise e


category_info: Dict[str, str] = {'name': 'Messages'}

commands: Dict[str, Callable[..., Coroutine[Any, Any, None]]] = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    }

version_info: str = "1.2.6-DEV"
