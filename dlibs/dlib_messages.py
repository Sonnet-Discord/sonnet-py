# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import time, asyncio, os, hashlib, string, io, gzip
import warnings
import copy as pycopy

import discord, lz4.frame

import lib_sonnetcommands

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, inc_statistics_better, load_embed_color, embed_colors, datetime_now
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions, grab_files, generate_reply_field, parse_boolean_strict
from lib_encryption_wrapper import encrypted_writer
from lib_compatibility import user_avatar_url
from lib_sonnetcommands import SonnetCommand, CommandCtx, CallCtx, ExecutableCtxT

from typing import List, Any, Dict, Optional, Callable, Tuple, Final, Literal, TypedDict, NewType, Union, Awaitable, Set, cast
import lib_lexdpyk_h as lexdpyk
import lib_constants as constants

ALLOWED_CHARS: Final = set(string.ascii_letters + string.digits + "-+;:'\"!@#$%^&()/.,?[{}]= ")


async def catch_logging_error(channel: discord.TextChannel, contents: discord.Embed, files: Optional[List[discord.File]] = None) -> None:
    try:
        await channel.send(embed=contents, files=(files or []))
    except discord.errors.Forbidden:
        pass
    except discord.errors.HTTPException:
        try:
            if files:
                await channel.send("There were files attached but they exceeded the guild filesize limit", embed=contents)
        except discord.errors.Forbidden:
            pass


def decide_to_file(msg: discord.Message, filename: str, behavior: Literal["none", "gzip", "text"]) -> Optional[discord.File]:
    if any(i not in ALLOWED_CHARS for i in msg.content) and behavior != "none":

        msgraw = msg.content.encode("utf8")

        if behavior == "text":
            buf = io.BytesIO(msgraw)
            filename += "txt"

        elif behavior == "gzip":
            buf = io.BytesIO()
            with gzip.GzipFile(filename + "txt", "wb", fileobj=buf) as txt:
                txt.write(msgraw)
            buf.seek(0)
            filename += "gz"

        return discord.File(buf, filename=filename)

    return None


message_and_edit_logs: Dict[Union[str, int], Union[str, List[List[Any]]]] = {
    0: "sonnet_message_and_edit_log",
    "text": [["message-log", ""], ["message-edit-log", ""], ["message-to-file-behavior", "text"], ["edit-log-is-message-log", "1"]]
    }


def message_file_log_behavior(conf: Optional[str]) -> Literal["text", "none", "gzip"]:
    # file log state
    tmp: Final = conf or "text"
    # Statically assert comparisons because mypy hates me
    # (and hates promoting a Final[str] to a Final[Literal[V]] when Final[str] == V = True)
    # Seriously how is that not a feature
    if tmp == "text": return "text"
    elif tmp == "gzip": return "gzip"
    elif tmp == "none": return "none"

    raise RuntimeError("Database entry for message-to-file-behavior is not text,gzip,none")


async def on_message_delete(message: discord.Message, **kargs: Any) -> None:

    client: Final[discord.Client] = kargs["client"]
    kernel_ramfs: Final[lexdpyk.ram_filesystem] = kargs["kernel_ramfs"]
    ramfs: Final[lexdpyk.ram_filesystem] = kargs["ramfs"]

    # Ignore bots
    if parse_skip_message(client, message, allow_bots=True):
        return
    elif not message.guild:
        return

    files: Optional[List[discord.File]] = grab_files(message.guild.id, message.id, kernel_ramfs, delete=True)

    # Change Optional[List[discord.File]] to List[discord.File]
    files = files if files is not None else []

    # Add logged_ prefix to make it impossible to namesnipe message content
    for i in files:
        i.filename = f"logged_{i.filename}"

    inc_statistics_better(message.guild.id, "on-message-delete", kernel_ramfs)

    db_configs = load_message_config(message.guild.id, kargs["ramfs"], datatypes=message_and_edit_logs)

    message_log: Optional[str] = db_configs["message-log"]
    behavior: Final = message_file_log_behavior(db_configs["message-to-file-behavior"])

    try:
        if not (message_log and (log_channel := client.get_channel(int(message_log)))):
            return
    except ValueError:
        try:
            await message.channel.send("ERROR: message-log config is corrupt in database, please reset")
        except discord.errors.Forbidden:
            pass
        return

    if not isinstance(log_channel, discord.TextChannel):
        return

    if v := decide_to_file(message, f"{message.id}_content.", behavior):
        files.append(v)

    message_embed: Final = discord.Embed(
        title=f"Message deleted in #{message.channel}", description=message.content[:constants.embed.description], color=load_embed_color(message.guild, embed_colors.deletion, ramfs)
        )

    # Parse for message lengths >2048 (discord now does 4000 hhhhhh)
    if len(message.content) > constants.embed.description:
        limend: Final = constants.embed.description + constants.embed.field.value
        message_embed.add_field(name="(Continued)", value=message.content[constants.embed.description:limend])

        if len(message.content) > limend:
            flimend: Final = limend + constants.embed.field.value
            message_embed.add_field(name="(Continued further)", value=message.content[limend:flimend])

    message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=user_avatar_url(message.author))

    if (r := message.reference) and (rr := r.resolved) and isinstance(rr, discord.Message):
        message_embed.add_field(name="Replying to:", value=f"{rr.author.mention} [(Link)]({rr.jump_url})")

    message_embed.set_footer(text=f"Message ID: {message.id}")
    message_embed.timestamp = message.created_at

    await catch_logging_error(log_channel, message_embed, files)


async def attempt_message_delete(message: discord.Message) -> None:
    try:
        await message.delete()
    except (discord.errors.Forbidden, discord.errors.NotFound):
        pass


async def grab_an_adult(discord_message: discord.Message, guild: discord.Guild, client: discord.Client, mconf: Dict[str, Any], ramfs: lexdpyk.ram_filesystem) -> None:

    if mconf["regex-notifier-log"] and (notify_log := client.get_channel(int(mconf["regex-notifier-log"]))):

        if not isinstance(notify_log, discord.TextChannel):
            return

        message_content: Final = generate_reply_field(discord_message)

        # Message has been grabbed, start generating embed
        message_embed: Final = discord.Embed(title=f"Auto Flagged Message in #{discord_message.channel}", description=message_content, color=load_embed_color(guild, embed_colors.primary, ramfs))

        message_embed.set_author(name=str(discord_message.author), icon_url=user_avatar_url(discord_message.author))
        message_embed.timestamp = discord_message.created_at

        # Grab files async
        awaitobjs: Final = [asyncio.create_task(i.to_file()) for i in discord_message.attachments]
        fileobjs: Final = [await i for i in awaitobjs]

        await catch_logging_error(notify_log, message_embed, fileobjs)


@lexdpyk.ToKernelArgs
async def on_message_edit(old_message: discord.Message, message: discord.Message, kctx: lexdpyk.KernelArgs) -> None:

    client: Final[discord.Client] = kctx.client
    ramfs: Final[lexdpyk.ram_filesystem] = kctx.ramfs
    kernel_ramfs: Final[lexdpyk.ram_filesystem] = kctx.kernel_ramfs

    # Ignore bots
    if parse_skip_message(client, message, allow_bots=True):
        return
    elif not message.guild:
        return

    inc_statistics_better(message.guild.id, "on-message-edit", kernel_ramfs)

    db_configs = load_message_config(message.guild.id, kctx.ramfs, datatypes=message_and_edit_logs)

    message_log_str: Final[Optional[str]] = db_configs["message-edit-log"] or (db_configs["message-log"] if parse_boolean_strict(db_configs["edit-log-is-message-log"]) else None)
    msgtofile_behavior: Final = message_file_log_behavior(db_configs["message-to-file-behavior"])

    # Skip logging if message is the same or mlog doesn't exist
    if message_log_str and not (old_message.content == message.content):
        if message_log := client.get_channel(int(message_log_str)):

            if not isinstance(message_log, discord.TextChannel):
                return

            files: Final = list(
                filter(None, (
                    decide_to_file(old_message, f"{message.id}_old_content.", msgtofile_behavior),
                    decide_to_file(message, f"{message.id}_new_content.", msgtofile_behavior),
                    ))
                )

            lim: Final[int] = constants.embed.field.value

            message_embed: Final = discord.Embed(title=f"Message edited in #{message.channel}", color=load_embed_color(message.guild, embed_colors.edit, ramfs))
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=user_avatar_url(message.author))

            old_msg: Final = (old_message.content or "NULL")
            message_embed.add_field(name="Old Message", value=(old_msg)[:lim], inline=False)
            if len(old_msg) > lim:
                message_embed.add_field(name="(Continued)", value=(old_msg)[lim:lim * 2], inline=False)

            msg: Final = (message.content or "NULL")
            message_embed.add_field(name="New Message", value=(msg)[:lim], inline=False)
            if len(msg) > lim:
                message_embed.add_field(name="(Continued)", value=(msg)[lim:lim * 2], inline=False)

            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime_now()
            asyncio.create_task(catch_logging_error(message_log, message_embed, files))

    # Check against blacklist
    mconf: Final = load_message_config(message.guild.id, ramfs)
    broke_blacklist, notify, infraction_type = parse_blacklist((message, mconf, ramfs), )

    if broke_blacklist:

        command_ctx: Final = CommandCtx(
            stats={},
            cmds=kctx.command_modules[0],
            ramfs=ramfs,
            bot_start=kctx.bot_start,
            dlibs=kctx.dynamiclib_modules[0],
            main_version=kctx.kernel_version,
            kernel_ramfs=kernel_ramfs,
            conf_cache={},
            verbose=False,
            cmds_dict=kctx.command_modules[1],
            automod=True
            )

        asyncio.create_task(attempt_message_delete(message))
        execargs: Final = [str(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"]
        await catch_ce(message, warn_missing(kctx.command_modules[1], mconf["blacklist-action"])(message, execargs, client, command_ctx))

    if notify:
        asyncio.create_task(grab_an_adult(message, message.guild, client, mconf, kctx.ramfs))


class BaseAntispamMeta(TypedDict):
    name: str
    message_count: int
    lifetime_millis: int


class FullAntispamMeta(BaseAntispamMeta, total=False):
    char_count: int


CharCount = NewType("CharCount", int)


def breaches_char_count(total_char_count: int, scan: FullAntispamMeta) -> bool:
    """
    Returns True in cases where scan does not have a char_count attr
    """
    if "char_count" in scan:
        return total_char_count > scan["char_count"]

    return True


def test_single_antispam(message: discord.Message, scan: FullAntispamMeta, ramfs: lexdpyk.ram_filesystem) -> bool:
    if not message.guild:
        raise RuntimeError("ERROR: antispam_check called on a non guild message")

    # Weird behavior(ultrabear): message.created_at.timestamp() returns unaware dt so we need to use datetime.utcnow for timestamps in antispam
    # Update(ultrabear): now that we use discord_datetime_now() we get an unaware dt or aware dt depending on dpy version

    # We drop a item if it is older than this
    #
    # We use the created_at timestamp here because this is the most recent message, and antispam should be based on durations created from message timestamps
    # If it was based on current polled time (previously it was) a lagspike could cause the bot to not trigger antispam on a set of messages where it should have
    #
    # We add one millisecond so that a lifetime of 0 will drop the current message
    droptime = (round(message.created_at.timestamp() * 1000) - scan["lifetime_millis"]) + 1

    try:
        data_dir = cast(Dict[int, List[Tuple[int, CharCount]]], ramfs.read_f(f"{message.guild.id}/{scan['name']}"))
        assert isinstance(data_dir, dict)
    except FileNotFoundError:
        data_dir = ramfs.create_f(f"{message.guild.id}/{scan['name']}", f_type=dict)

    user_data = data_dir.get(message.author.id, [])

    # add current message
    user_data.append((round(message.created_at.timestamp() * 1000), CharCount(len(message.content))), )

    new_user_data = []
    total_char_count = 0

    for (timestamp_millis, char_count) in user_data:

        if timestamp_millis > droptime:
            total_char_count += char_count
            new_user_data.append((timestamp_millis, char_count), )

    # load new data
    data_dir[message.author.id] = new_user_data

    return breaches_char_count(total_char_count, scan) and len(new_user_data) >= scan["message_count"]


def antispam_check(message: discord.Message, ramfs: lexdpyk.ram_filesystem, antispam: List[str], charantispam: List[str]) -> Tuple[bool, Literal["", "Antispam", "CharAntispam"]]:

    antispam_data: FullAntispamMeta = {
        "name": "asam",
        "message_count": int(antispam[0]),
        "lifetime_millis": int(float(antispam[1]) * 1000),
        }

    char_antispam_data: FullAntispamMeta = {
        "name": "casam",
        "message_count": int(charantispam[0]),
        "lifetime_millis": int(float(charantispam[1]) * 1000),
        "char_count": int(charantispam[2]),
        }

    if test_single_antispam(message, antispam_data, ramfs):
        return (True, "Antispam")
    elif test_single_antispam(message, char_antispam_data, ramfs):
        return (True, "CharAntispam")

    return (False, "")


async def download_file(nfile: discord.Attachment, compression: Any, encryption: encrypted_writer, filename: str, ramfs: lexdpyk.ram_filesystem, guild_id: int, message_id: int) -> None:

    await nfile.save(compression, seek_begin=False)
    compression.close()
    encryption.close()

    # Keep message files in cache for 60 minutes, or 1 hour
    # This was previously 30 minutes as it was seen as an average response time,
    # but has been raised to account for some edge case poor response times from moderators
    # This did not show significant disk use at 30 minutes, so double that time should be fine
    await asyncio.sleep(60 * 60)

    try:
        os.remove(filename)
    except FileNotFoundError:
        pass
    try:
        ramfs.rmdir(f"{guild_id}/files/{message_id}")
    except FileNotFoundError:
        pass


async def log_message_files(message: discord.Message, kernel_ramfs: lexdpyk.ram_filesystem) -> None:
    if not message.guild:
        return

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
        file_loc = f"./datastore/{message.guild.id}-{pointer}.cache.db"
        pointerfile.write(file_loc.encode("utf8"))

        # Create encryption and compression wrappers (raw -> compressed -> encrypted -> disk)
        encryption_fileobj = encrypted_writer(file_loc, key, iv)
        compression_fileobj = lz4.frame.LZ4FrameFile(filename=encryption_fileobj, mode="wb")

        # Do file downloading in async
        asyncio.create_task(download_file(i, compression_fileobj, encryption_fileobj, file_loc, kernel_ramfs, message.guild.id, message.id))


def warn_missing(command_dict: Dict[str, Any], argument: str, /) -> ExecutableCtxT:
    """
    Attempts to grab a command, if it cannot it will send a warning to terminal that it is missing and return a null callback
    """

    try:
        return CallCtx(command_dict[argument]["execute"])
    except KeyError:

        warnings.warn(f"WARN: Automod command {argument} was missing when it was queried")

        async def dummy(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:
            return None

        return dummy


async def catch_ce(err_rsp: discord.Message, promise: Awaitable[Any]) -> None:

    try:
        await promise
    except lib_sonnetcommands.CommandError as ce:
        try:
            await err_rsp.channel.send(str(ce))
        except discord.errors.HTTPException:
            pass
    except discord.errors.Forbidden:
        # ignore permission errors
        pass



@lexdpyk.ToKernelArgs
async def on_message(message: discord.Message, kernel_args: lexdpyk.KernelArgs) -> None:

    client: Final = kernel_args.client
    ramfs: Final = kernel_args.ramfs

    command_modules, command_modules_dict = kernel_args.command_modules

    # Statistics.
    stats: Final[Dict[str, int]] = {"start": round(time.time() * 100000)}

    if parse_skip_message(client, message, allow_bots=True):
        return
    elif not message.guild:
        return
    elif not client.user:
        return

    inc_statistics_better(message.guild.id, "on-message", kernel_args.kernel_ramfs)

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf: Final = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against automod
    stats["start-automod"] = round(time.time() * 100000)

    spammer, spamstr = antispam_check(message, ramfs, mconf["antispam"], mconf["char-antispam"])

    message_deleted: bool = False

    command_ctx: Final = CommandCtx(
        stats=stats,
        cmds=command_modules,
        ramfs=ramfs,
        bot_start=kernel_args.bot_start,
        dlibs=kernel_args.dynamiclib_modules[0],
        main_version=kernel_args.kernel_version,
        kernel_ramfs=kernel_args.kernel_ramfs,
        conf_cache=mconf,
        verbose=True,
        cmds_dict=command_modules_dict,
        automod=False
        )

    automod_ctx: Final = pycopy.copy(command_ctx)
    automod_ctx.verbose = False
    automod_ctx.automod = True

    # If blacklist broken generate infraction
    broke_blacklist, notify, infraction_type = parse_blacklist((message, mconf, ramfs), )
    if broke_blacklist:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        execargs = [str(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"]
        asyncio.create_task(catch_ce(message, warn_missing(command_modules_dict, mconf["blacklist-action"])(message, execargs, client, automod_ctx)))

    if spammer:
        message_deleted = True
        asyncio.create_task(attempt_message_delete(message))
        with db_hlapi(message.guild.id) as db:
            if not db.is_muted(userid=message.author.id):
                execargs = [str(message.author.id), mconf["antispam-time"], "[AUTOMOD]", spamstr]
                asyncio.create_task(catch_ce(message, warn_missing(command_modules_dict, mconf["antispam-action"])(message, execargs, client, automod_ctx)))

    if notify:
        asyncio.create_task(grab_an_adult(message, message.guild, client, mconf, ramfs))

    stats["end-automod"] = round(time.time() * 100000)

    # Log files if not deleted
    if not message_deleted:
        asyncio.create_task(log_message_files(message, kernel_args.kernel_ramfs))

    # END blacklist loop

    # disallow bots to send commands, but still run blacklist on their messages
    # this is primarily motivated by adding pluralkit support, as their messages
    # will still be blacklisted on and are thus safe in a server that relies on sonnet blacklisting
    if message.author.bot:
        return

    # START command processing loop

    mention_prefix: Final = message.content.startswith(f"<@{client.user.id}>") or message.content.startswith(f"<@!{client.user.id}>")

    # Check if this is meant for us.
    if not (message.content.startswith(mconf["prefix"])) or message_deleted:
        if client.user.mentioned_in(message) and str(client.user.id) == message.content.strip("<@!>"):
            try:
                await message.channel.send(f"My prefix for this guild is {mconf['prefix']}")
            except discord.errors.Forbidden:
                pass  # Nothing we can do if we lack perms to speak
            return
        elif not mention_prefix:
            return

    # Split into cmds and arguments.
    arguments: Final = message.content.split()
    if mention_prefix:
        try:
            # delete mention
            del arguments[0]
            command = arguments[0]
        except IndexError:
            return
    else:
        command = arguments[0][len(mconf["prefix"]):]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict:

        cmd: Final = SonnetCommand(command_modules_dict[command], command_modules_dict)

        if not await parse_permissions(message, mconf, cmd.permission):
            return  # Return on no perms

        try:
            stats["end"] = round(time.time() * 100000)

            try:
                await cmd.execute_ctx(message, arguments, client, command_ctx)
            except lib_sonnetcommands.CommandError as ce:
                asyncio.create_task(ce.send(message))

            cmd.sweep_cache(ramfs, message.guild)

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


category_info: Final[Dict[str, str]] = {'name': 'Messages'}

commands: Final[Dict[str, Callable[..., Any]]] = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    }

version_info: Final = "2.0.1-DEV"
