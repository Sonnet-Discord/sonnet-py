# Administration commands.
# bredo, 2020

import importlib

import discord, os, glob
from datetime import datetime
import json, gzip, io, time

from sonnet_cfg import GLOBAL_PREFIX

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_parsers
importlib.reload(lib_parsers)
import lib_loaders
importlib.reload(lib_loaders)

from lib_parsers import parse_boolean, update_log_channel, parse_role
from lib_loaders import read_vnum, write_vnum
from lib_db_obfuscator import db_hlapi


async def joinlog_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "join-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


async def inflog_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "infraction-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


async def msglog_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "message-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


async def notifier_log_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "regex-notifier-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


async def username_log_change(message, args, client, **kwargs):
    try:
        await update_log_channel(message, args, client, "username-log", verbose=kwargs["verbose"])
    except lib_parsers.errors.log_channel_update_error:
        return


class gdpr_functions:
    async def delete(message, guild_id, ramfs, kramfs):

        with db_hlapi(message.guild.id) as database:
            database.delete_guild_db()

        ramfs.rmdir(f"{guild_id}")
        kramfs.rmdir(f"{guild_id}")

        for i in glob.glob(f"./datastore/{guild_id}-*.cache.db"):
            os.remove(i)

        await message.channel.send(
            f"Deleted database for guild {message.guild.id}\nPlease note that when the bot recieves a message from this guild it will generate a cache and statistics file again\nAs we delete all data on this guild, there is no way Sonnet should be able to tell it is not supposed to be on this server\nTo fully ensure sonnet does not store any data on this server, delete the db and kick the bot immediately, or contact the bot owner to have the db manually deleted after kicking the bot"
            )

    async def download(message, guild_id, ramfs, kramfs):

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
        antispam.seek(0)

        # Finalize discord file objs
        fileobj_db = discord.File(db, filename="database.gz")
        fileobj_antispam = discord.File(antispam, filename="antispam.u8_u8.bin")

        # Send data
        await message.channel.send(f"Grabbing DB took: {round((time.time()-timestart)*100000)/100}ms", files=[fileobj_db, fileobj_antispam])


async def gdpr_database(message, args, client, **kwargs):

    ramfs = kwargs["ramfs"]

    if len(args) >= 2:
        command = args[0]
        confirmation = args[1]
    elif len(args) >= 1:
        command = args[0]
        confirmation = None
    else:
        command = None

    PREFIX = kwargs["conf_cache"]["prefix"]

    commands_dict = {"delete": gdpr_functions.delete, "download": gdpr_functions.download}
    if command and command in commands_dict.keys():
        if confirmation and confirmation == str(message.guild.id):
            await commands_dict[command](message, message.guild.id, ramfs, kwargs["kernel_ramfs"])
        else:
            await message.channel.send(f"Please provide the guildid to confirm\nEx: `{PREFIX}gdpr {command} {message.guild.id}`")
    else:
        message_embed = discord.Embed(title="GDPR COMMANDS", color=0xADD8E6)
        message_embed.add_field(name=f"{PREFIX}gdpr download <guildid>", value="Download the databases of this guild", inline=False)
        message_embed.add_field(name=f"{PREFIX}gdpr delete <guildid>", value="Delete the databases of this guild and clear cache", inline=False)
        await message.channel.send(embed=message_embed)


async def set_view_infractions(message, args, client, **kwargs):

    if args:
        gate = parse_boolean(args[0])
        with db_hlapi(message.guild.id) as database:
            database.add_config("member-view-infractions", int(gate))
    else:
        with db_hlapi(message.guild.id) as database:
            gate = bool(int(database.grab_config("member-view-infractions") or 0))

    if kwargs["verbose"]: await message.channel.send(f"Member View Own Infractions is set to {gate}")


async def set_prefix(message, args, client, **kwargs):

    if args:
        prefix = args[0]
        with db_hlapi(message.guild.id) as database:
            database.add_config("prefix", prefix)
    else:
        with db_hlapi(message.guild.id) as database:
            prefix = database.grab_config("prefix")

    if kwargs["verbose"]: await message.channel.send(f"Prefix set to `{prefix}`")


async def set_mute_role(message, args, client, **kwargs):

    await parse_role(message, args, "mute-role", verbose=kwargs["verbose"])


async def set_admin_role(message, args, client, **kwargs):

    await parse_role(message, args, "admin-role", verbose=kwargs["verbose"])


async def set_moderator_role(message, args, client, **kwargs):

    await parse_role(message, args, "moderator-role", verbose=kwargs["verbose"])


category_info = {'name': 'administration', 'pretty_name': 'Administration', 'description': 'Administration commands.'}

commands = {
    'message-log': {
        'pretty_name': 'message-log <channel>',
        'description': 'Change message log',
        'permission': 'administrator',
        'cache': 'keep',
        'execute': msglog_change
        },
    'leave-log': {
        'alias': 'join-log'
        },
    'join-log':
        {
            'pretty_name': 'join-log <channel>',
            'description': 'Change join log',
            'rich_description': 'This log channel logs member joins and member leaves',
            'permission': 'administrator',
            'cache': 'keep',
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
    'username-log': {
        'pretty_name': 'username-log <channel>',
        'description': 'Change username log',
        'permission': 'administrator',
        'cache': 'keep',
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

version_info = "1.2.1"
