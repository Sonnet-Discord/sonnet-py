# Administration commands.
# bredo, 2020

import importlib

import discord, os, glob
import json, gzip, io, time, math

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)
import lib_constants

importlib.reload(lib_constants)

from lib_parsers import parse_boolean, update_log_channel, parse_role, paginate_noexcept
from lib_loaders import load_embed_color, embed_colors
from lib_db_obfuscator import db_hlapi
from lib_sonnetconfig import BOT_NAME
from lib_sonnetcommands import CommandCtx
import lib_constants as constants

from typing import List, Dict, Tuple, Final
import lib_lexdpyk_h as lexdpyk

InfracModifierT = Dict[str, Tuple[str, str]]


def maxlen(s: str, n: int, name: str) -> str:
    if len(s) > n:
        raise lib_sonnetcommands.CommandError(f"ERROR: {name} argument exceeds maxsize of {n}")
    return s


async def boolean_to_db_helper(message: discord.Message, args: List[str], db_name: str, pretty_name: str, default: bool, verbose: bool) -> int:
    if not message.guild:
        return 1

    if args:

        pb = parse_boolean(args[0])

        if pb is None:
            raise lib_sonnetcommands.CommandError("ERROR: Could not parse boolean value")

        with db_hlapi(message.guild.id) as db:
            db.add_config(db_name, str(int(pb)))

        if verbose: await message.channel.send(f"Set {pretty_name} to {pb}")

    else:
        with db_hlapi(message.guild.id) as db:
            gate = bool(int(db.grab_config(db_name) or int(default)))

        if verbose: await message.channel.send(f"{pretty_name} is set to {gate}")

    return 0


async def add_infrac_modifier(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if len(args) >= 3:
        key = maxlen(args[0], 64, "Key")
        title = maxlen(args[1], 64, "Title")
        value = maxlen(' '.join(args[2:]), 512, "Value")

        with db_hlapi(message.guild.id) as db:
            conf_name: Final = "infraction-modifiers"
            data: InfracModifierT = json.loads(db.grab_config(conf_name) or "{}")

            if len(data) >= 32:
                raise lib_sonnetcommands.CommandError("ERROR: Cannot have more than 32 infraction modifiers")

            data[key] = (title, value)

            db.add_config(conf_name, json.dumps(data))

        await message.channel.send(f"Added new infraction modifier with key {key}")
        return 0

    else:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_args.not_enough)


async def delete_infrac_modifier(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if args:
        key = args[0]

        with db_hlapi(message.guild.id) as db:
            conf_name: Final = "infraction-modifiers"
            data: InfracModifierT = json.loads(db.grab_config(conf_name) or "{}")

            try:
                del data[key]
            except KeyError:
                raise lib_sonnetcommands.CommandError("ERROR: No such infraction modifier key")

            db.add_config(conf_name, json.dumps(data))

        await message.channel.send(f"Deleted infraction modifier with key {key}")
        return 0

    else:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_args.not_enough)


async def list_infrac_modifiers(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    try:
        p = int(args[0]) - 1 if args else 0
    except ValueError:
        raise lib_sonnetcommands.CommandError("ERROR: Page parsing failed")

    with db_hlapi(message.guild.id) as db:
        data: InfracModifierT = json.loads(db.grab_config("infraction-modifiers") or "{}")

    if not data:
        await message.channel.send("No infraction modifiers in db")
        return 0

    renderable = sorted(((i, v[0], v[1]) for i, v in data.items()), key=lambda v: v[0])

    def render(it: Tuple[str, str, str]) -> str:
        return " ".join(it)

    await message.channel.send(f"Modifiers: {len(data)} (page {p+1} of {math.ceil(len(data)/16)})```\n{paginate_noexcept(renderable, p, 16, 1950, render)}```")
    return 0


async def set_show_mutetime(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await boolean_to_db_helper(message, args, "show-mutetime", "Show Mutetime", False, ctx.verbose)


async def joinlog_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "join-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def leave_log_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "leave-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def inflog_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "infraction-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def msglog_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "message-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def message_edit_log_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "message-edit-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def notifier_log_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "regex-notifier-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def username_log_change(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    try:
        await update_log_channel(message, args, client, "username-log", verbose=ctx.verbose)
        return 0
    except lib_parsers.errors.log_channel_update_error:
        return 1


class gdpr_functions:
    __slots__ = "commands",

    def __init__(self) -> None:
        self.commands = {"delete": self.delete, "download": self.download}

    async def delete(self, message: discord.Message, guild_id: int, ramfs: lexdpyk.ram_filesystem, kramfs: lexdpyk.ram_filesystem) -> None:
        if not message.guild:
            return

        with db_hlapi(message.guild.id) as database:
            database.delete_guild_db()

        ramfs.rmdir(f"{guild_id}")
        kramfs.rmdir(f"{guild_id}")

        for i in glob.glob(f"./datastore/{guild_id}-*.cache.db"):
            os.remove(i)

        await message.channel.send(
            f"""Deleted database for guild {message.guild.id}
Please note that when the bot receives a message from this guild it will generate a cache and statistics file again
As we delete all data on this guild, there is no way {BOT_NAME} should be able to tell it is not supposed to be on this server
To fully ensure {BOT_NAME} does not store any data on this server, delete the db and kick the bot immediately, or contact the bot owner to have the db manually deleted after kicking the bot"""
            )

    async def download(self, message: discord.Message, guild_id: int, ramfs: lexdpyk.ram_filesystem, kramfs: lexdpyk.ram_filesystem) -> None:

        timestart = time.time()

        with db_hlapi(guild_id) as database:
            dbdict = database.download_guild_db()

        # Convert db to compressed json
        db = io.BytesIO()
        with gzip.GzipFile(filename=f"{guild_id}.db.json.gz", mode="wb", fileobj=db) as txt:
            txt.write(json.dumps(dbdict, indent=4).encode("utf8"))
        db.seek(0)

        # Add cache files
        antispam = ramfs.read_f(f"{guild_id}/asam")
        assert isinstance(antispam, io.BytesIO)
        antispam.seek(0)
        charantispam = ramfs.read_f(f"{guild_id}/casam")
        assert isinstance(charantispam, io.BytesIO)
        charantispam.seek(0)

        # Finalize discord file objs
        fileobj_db = discord.File(db, filename="database.gz")
        fileobj_antispam = discord.File(io.BytesIO(antispam.read()), filename="antispam.vnum_x2.bin")
        fileobj_cantispam = discord.File(io.BytesIO(charantispam.read()), filename="charantispam.vnum_x3.bin")

        # Send data
        try:
            await message.channel.send(f"Grabbing DB took: {round((time.time()-timestart)*100000)/100}ms", files=[fileobj_db, fileobj_antispam, fileobj_cantispam])
        except discord.errors.HTTPException:
            await message.channel.send(
                """ERROR: There was an error uploading the files, if you have a large infraction database this could be caused by discords file size limitation
Please contact the bot owner directly to download your guilds database
Or if discord experienced a lag spike, consider retrying as the network may have gotten corrupted"""
                )


async def gdpr_database(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs

    if len(args) >= 2:
        command = args[0]
        confirmation = args[1]
    elif len(args) >= 1:
        command = args[0]
        confirmation = ""
    else:
        command = ""
        confirmation = ""

    PREFIX = ctx.conf_cache["prefix"]

    gdprfunctions = gdpr_functions()
    if command and command in gdprfunctions.commands:
        if confirmation and confirmation == str(message.guild.id):
            await gdprfunctions.commands[command](message, message.guild.id, ramfs, ctx.kernel_ramfs)
        else:
            await message.channel.send(f"Please provide the guild id to confirm\nEx: `{PREFIX}gdpr {command} {message.guild.id}`")
    else:
        message_embed = discord.Embed(title="GDPR COMMANDS", color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs))
        message_embed.add_field(name=f"{PREFIX}gdpr download <guild id>", value="Download the databases of this guild", inline=False)
        message_embed.add_field(name=f"{PREFIX}gdpr delete <guild id>", value="Delete the databases of this guild and clear cache", inline=False)
        await message.channel.send(embed=message_embed)

    return 0


async def set_view_infractions(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await boolean_to_db_helper(message, args, "member-view-infractions", "Member View own Infractions", False, ctx.verbose)


async def set_prefix(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if args:
        prefix = args[0]
        with db_hlapi(message.guild.id) as database:
            database.add_config("prefix", prefix)
    else:
        prefix = ctx.conf_cache["prefix"]

    if ctx.verbose: await message.channel.send(f"Prefix set to `{prefix}`")
    return 0


async def set_mute_role(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await parse_role(message, args, "mute-role", verbose=ctx.verbose)


async def set_admin_role(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await parse_role(message, args, "admin-role", verbose=ctx.verbose)


async def set_moderator_role(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await parse_role(message, args, "moderator-role", verbose=ctx.verbose)


async def set_filelog_behavior(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if args:
        if (state := args[0]) in ["none", "text", "gzip"]:
            with db_hlapi(message.guild.id) as db:
                db.add_config("message-to-file-behavior", state)
            await message.channel.send(f"Message-to-file log status has been updated to {state}")
        else:
            raise lib_sonnetcommands.CommandError("ERROR: Passed behavior is not valid, only (text|gzip|none) are valid")
    else:
        with db_hlapi(message.guild.id) as db:
            state = db.grab_config("message-to-file-behavior") or "text"
        await message.channel.send(f"Message-to-file log status is currently {state}")

    return 0


async def set_moderator_protect(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    return await boolean_to_db_helper(message, args, "moderator-protect", "Moderator Protect", False, ctx.verbose)


category_info = {'name': 'administration', 'pretty_name': 'Administration', 'description': 'Administration commands.'}

commands = {
    'set-show-mutetime':
        {
            'pretty_name': 'set-show-mutetime <bool>',
            'description': 'Set whether to show the mute time to a user who has been muted',
            'permission': 'administrator',
            'execute': set_show_mutetime,
            },
    'list-infraction-modifiers': {
        'pretty_name': 'list-infraction-modifiers [page]',
        'description': 'list all infraction modifiers',
        'permission': 'moderator',
        'execute': list_infrac_modifiers,
        },
    'rm-infraction-modifier':
        {
            'pretty_name': 'rm-infraction-modifier <key> <title> <value>',
            'description': 'Delete an infraction modifier with the given key',
            'permission': 'administrator',
            'execute': delete_infrac_modifier,
            },
    'add-infraction-modifier':
        {
            'pretty_name': 'add-infraction-modifier <key> <title> <value>',
            'description': 'Add a new infraction modifier with the given key, title, and value',
            'permission': 'administrator',
            'execute': add_infrac_modifier,
            },
    'set-filelog-behaviour': {
        'alias': 'set-filelog-behavior',
        },
    'set-filelog-behavior':
        {
            'pretty_name': 'set-filelog-behavior [text|gzip|none]',
            'description': 'Set the message to file log behavior to store text, gzip, or not store',
            'permission': 'administrator',
            'execute': set_filelog_behavior,
            },
    'message-edit-log':
        {
            'pretty_name': 'message-edit-log <channel>',
            'description': 'Change message edit log, overloads message-log',
            'permission': 'administrator',
            'execute': message_edit_log_change
            },
    'message-log': {
        'pretty_name': 'message-log <channel>',
        'description': 'Change message log',
        'permission': 'administrator',
        'execute': msglog_change
        },
    'leave-log':
        {
            'pretty_name': 'leave-log <channel>',
            'description': 'Change leave log, overloads join-log',
            'rich_description': 'Set the leave log, diverts leave logs from join log to leave log',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_userupdate_log',
            'execute': leave_log_change
            },
    'join-log':
        {
            'pretty_name': 'join-log <channel>',
            'description': 'Change join log',
            'rich_description': 'This log channel logs member joins and member leaves',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_userupdate_log',
            'execute': joinlog_change
            },
    'infraction-log': {
        'pretty_name': 'infraction-log <channel>',
        'description': 'Change infraction log',
        'permission': 'administrator',
        'execute': inflog_change
        },
    'notifier-log': {
        'pretty_name': 'notifier-log <channel>',
        'description': 'Change notifier log',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': notifier_log_change
        },
    'username-log':
        {
            'pretty_name': 'username-log <channel>',
            'description': 'Change username log',
            'permission': 'administrator',
            'cache': 'direct:(f)caches/sonnet_userupdate_log',
            'execute': username_log_change
            },
    'gdpr': {
        'pretty_name': 'gdpr',
        'description': 'Enforce your GDPR rights, Server Owner only',
        'permission': 'owner',
        'cache': 'purge',
        'execute': gdpr_database
        },
    'viewinfractions': {
        'alias': 'set-viewinfractions'
        },
    'set-viewinfractions':
        {
            'pretty_name': 'set-viewinfractions <bool>',
            'description': 'Set whether members of the guild can view their own infraction count',
            'permission': 'administrator',
            'execute': set_view_infractions
            },
    'set-prefix': {
        'pretty_name': 'set-prefix <prefix>',
        'description': 'Set the Guild prefix',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': set_prefix
        },
    'set-muterole': {
        'pretty_name': 'set-muterole <role>',
        'description': 'Set the mute role',
        'permission': 'administrator',
        'execute': set_mute_role
        },
    'set-adminrole': {
        'pretty_name': 'set-adminrole <role>',
        'description': 'Set the administrator role',
        'permission': 'owner',
        'cache': 'regenerate',
        'execute': set_admin_role
        },
    'set-modrole': {
        'pretty_name': 'set-modrole <role>',
        'description': 'Set the moderator role',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': set_moderator_role
        },
    'set-moderator-protect':
        {
            'pretty_name': 'set-moderator-protect <bool>',
            'description': 'Set whether to disallow infractions being given to moderator+ members, disabled by default',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_moderator_protect,
            }
    }

version_info: str = "1.2.14-DEV"
