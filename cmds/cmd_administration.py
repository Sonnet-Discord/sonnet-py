# Administration commands.
# bredo, 2020

import importlib

import discord, os, glob
import json, gzip, io, time

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)

from lib_parsers import parse_boolean, update_log_channel, parse_role
from lib_loaders import load_embed_color, embed_colors
from lib_db_obfuscator import db_hlapi

from typing import Any, List


async def joinlog_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "join-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def leave_log_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "leave-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def inflog_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "infraction-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def msglog_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "message-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def message_edit_log_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "message-edit-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def notifier_log_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "regex-notifier-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


async def username_log_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await update_log_channel(message, args, client, "username-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return 1


class gdpr_functions:
    def __init__(self) -> None:
        self.commands = {"delete": self.delete, "download": self.download}

    async def delete(self, message: discord.Message, guild_id: int, ramfs: Any, kramfs: Any) -> None:

        with db_hlapi(message.guild.id) as database:
            database.delete_guild_db()

        ramfs.rmdir(f"{guild_id}")
        kramfs.rmdir(f"{guild_id}")

        for i in glob.glob(f"./datastore/{guild_id}-*.cache.db"):
            os.remove(i)

        await message.channel.send(
            f"""Deleted database for guild {message.guild.id}
Please note that when the bot receives a message from this guild it will generate a cache and statistics file again
As we delete all data on this guild, there is no way Sonnet should be able to tell it is not supposed to be on this server
To fully ensure sonnet does not store any data on this server, delete the db and kick the bot immediately, or contact the bot owner to have the db manually deleted after kicking the bot"""
            )

    async def download(self, message: discord.Message, guild_id: int, ramfs: Any, kramfs: Any) -> None:

        timestart = time.time()

        with db_hlapi(guild_id) as database:
            dbdict = database.download_guild_db()

        # Convert db to compressed json
        db = io.BytesIO()
        with gzip.GzipFile(filename=f"{guild_id}.db.json.gz", mode="wb", fileobj=db) as txt:
            txt.write(json.dumps(dbdict, indent=4).encode("utf8"))
        db.seek(0)

        # Add cache files
        antispam: io.BytesIO = ramfs.read_f(f"{guild_id}/asam")
        antispam.seek(0)
        charantispam: io.BytesIO = ramfs.read_f(f"{guild_id}/casam")
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
                """ERROR: There was an error uploading the files, if you have a large infraction database this could be caused by discords filesize limitation
Please contact the bot owner directly to download your guilds database
Or if discord experienced a lag spike, consider retrying as the network may have gotten corrupted"""
                )


async def gdpr_database(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    ramfs = kwargs["ramfs"]

    if len(args) >= 2:
        command = args[0]
        confirmation = args[1]
    elif len(args) >= 1:
        command = args[0]
        confirmation = ""
    else:
        command = ""

    PREFIX = kwargs["conf_cache"]["prefix"]

    gdprfunctions = gdpr_functions()
    if command and command in gdprfunctions.commands:
        if confirmation and confirmation == str(message.guild.id):
            await gdprfunctions.commands[command](message, message.guild.id, ramfs, kwargs["kernel_ramfs"])
        else:
            await message.channel.send(f"Please provide the guild id to confirm\nEx: `{PREFIX}gdpr {command} {message.guild.id}`")
    else:
        message_embed = discord.Embed(title="GDPR COMMANDS", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
        message_embed.add_field(name=f"{PREFIX}gdpr download <guild id>", value="Download the databases of this guild", inline=False)
        message_embed.add_field(name=f"{PREFIX}gdpr delete <guild id>", value="Delete the databases of this guild and clear cache", inline=False)
        await message.channel.send(embed=message_embed)


async def set_view_infractions(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if args:
        gate = parse_boolean(args[0])
        with db_hlapi(message.guild.id) as database:
            database.add_config("member-view-infractions", str(int(gate)))
    else:
        with db_hlapi(message.guild.id) as database:
            gate = bool(int(database.grab_config("member-view-infractions") or 0))

    if kwargs["verbose"]: await message.channel.send(f"Member View Own Infractions is set to {gate}")


async def set_prefix(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if args:
        prefix = args[0]
        with db_hlapi(message.guild.id) as database:
            database.add_config("prefix", prefix)
    else:
        prefix = kwargs["conf_cache"]["prefix"]

    if kwargs["verbose"]: await message.channel.send(f"Prefix set to `{prefix}`")


async def set_mute_role(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    return await parse_role(message, args, "mute-role", verbose=kwargs["verbose"])


async def set_admin_role(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    return await parse_role(message, args, "admin-role", verbose=kwargs["verbose"])


async def set_moderator_role(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    return await parse_role(message, args, "moderator-role", verbose=kwargs["verbose"])


category_info = {'name': 'administration', 'pretty_name': 'Administration', 'description': 'Administration commands.'}

commands = {
    'message-edit-log':
        {
            'pretty_name': 'message-edit-log <channel>',
            'description': 'Change message edit log, overloads message-log',
            'permission': 'administrator',
            'cache': 'keep',
            'execute': message_edit_log_change
            },
    'message-log': {
        'pretty_name': 'message-log <channel>',
        'description': 'Change message log',
        'permission': 'administrator',
        'cache': 'keep',
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
        'cache': 'keep',
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
            'cache': 'keep',
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
        'cache': 'keep',
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
        }
    }

version_info: str = "1.2.5"
