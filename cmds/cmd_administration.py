# Administration commands.
# bredo, 2020

import discord, os
from datetime import datetime
import json, gzip, io, time

from sonnet_cfg import GLOBAL_PREFIX
from lib_parsers import parse_boolean, update_log_channel
from lib_loaders import load_message_config
from lib_db_obfuscator import db_hlapi


async def recreate_db(message, args, client, stats, cmds, ramfs):

    with db_hlapi(message.guild.id) as db:
        db.create_guild_db()

    await message.channel.send("Done")


async def inflog_change(message, args, client, stats, cmds, ramfs):
    try:
        await update_log_channel(message, args, client, "infraction-log")
    except RuntimeError:
        return


async def joinlog_change(message, args, client, stats, cmds, ramfs):
    try:
        await update_log_channel(message, args, client, "join-log")
    except RuntimeError:
        return


async def msglog_change(message, args, client, stats, cmds, ramfs):
    try:
        await update_log_channel(message, args, client, "message-log")
    except RuntimeError:
        return


class gdpr_functions:

    async def delete(message, guild_id):

        database = db_hlapi(message.guild.id)
        database.delete_guild_db()

        await message.channel.send(f"Deleted database for guild {message.guild.id}")

    async def download(message, guild_id):

        timestart = time.time()
        with db_hlapi(guild_id) as database:
            dbdict = database.download_guild_db()

        # Convert to compressed json
        file_to_upload = io.BytesIO()
        with gzip.GzipFile(filename=f"{guild_id}.db.json.gz", mode="wb", fileobj=file_to_upload) as txt:
            txt.write(json.dumps(dbdict, indent=4).encode("utf8"))
        file_to_upload.seek(0)

        # Finalize discord file obj
        fileobj = discord.File(file_to_upload, filename="database.gz")

        await message.channel.send(f"Grabbing DB took: {round((time.time()-timestart)*100000)/100}ms", file=fileobj)


async def gdpr_database(message, args, client, stats, cmds, ramfs):

    if len(args) >= 2:
        command = args[0]
        confirmation = args[1]
    elif len(args) >= 1:
        command = args[0]
        confirmation = None
    else:
        command = None

    PREFIX = load_message_config(message.guild.id, ramfs)["prefix"]

    commands_dict = {"delete": gdpr_functions.delete, "download": gdpr_functions.download}
    if command and command in commands_dict.keys():
        if confirmation and confirmation == str(message.guild.id):
            await commands_dict[command](message, message.guild.id)
        else:
            await message.channel.send(f"Please provide the guildid to confirm\nEx: `{PREFIX}gdpr {command} {message.guild.id}`")
    else:
        message_embed = discord.Embed(title="GDPR COMMANDS", color=0xADD8E6)
        message_embed.add_field(name=f"{PREFIX}gdpr download <guildid>", value="Download the infraction and config databases of this guild", inline=False)
        message_embed.add_field(name=f"{PREFIX}gdpr delete <guildid>", value="Delete the infraction and config databases of this guild and clear cache", inline=False)
        await message.channel.send(embed=message_embed)


async def set_view_infractions(message, args, client, stats, cmds, ramfs):

    if args:
        gate = parse_boolean(args[0])
    else:
        gate = False

    with db_hlapi(message.guild.id) as database:
        database.add_config("member-view-infractions", int(gate))

    await message.channel.send(f"Member View Own Infractions set to {gate}")


async def set_prefix(message, args, client, stats, cmds, ramfs):

    if args:
        prefix = args[0]
    else:
        prefix = GLOBAL_PREFIX

    with db_hlapi() as database:
        database.add_config("prefix", prefix)

    await message.channel.send(f"Updated prefix to `{prefix}`")


async def set_mute_role(message, args, client, stats, cmds, ramfs):
    
    if args:
        role = args[0].strip("<@&>")
    else:
        await message.channel.send("No role supplied")
        return

    try:
        role = int(role)
    except ValueError:
        await message.channel.send("Invalid role")
        return

    with db_hlapi(message.guild.id) as database:
        database.add_config("mute-role", role)

    await message.channel.send(f"Updated Mute role to {role}")

category_info = {
    'name': 'administration',
    'pretty_name': 'Administration',
    'description': 'Administration commands.'
}


commands = {
    'recreate-db': {
        'pretty_name': 'recreate-db',
        'description': 'Recreate the database if it doesn\'t exist',
        'permission':'administrator',
        'cache':'keep',
        'execute': recreate_db
    },
    'message-log': {
        'pretty_name': 'message-log',
        'description': 'Change message log for this guild.',
        'permission':'administrator',
        'cache':'keep',
        'execute': msglog_change
    },
    'infraction-log': {
        'pretty_name': 'infraction-log',
        'description': 'Change infraction log for this guild.',
        'permission':'administrator',
        'cache':'keep',
        'execute': inflog_change
    },
    'join-log': {
        'pretty_name': 'join-log',
        'description': 'Change join log for this guild.',
        'permission':'administrator',
        'cache':'keep',
        'execute': joinlog_change
    },
    'gdpr': {
        'pretty_name': 'gdpr',
        'description': 'Enforce your GDPR rights, Server Owner only',
        'permission':'owner',
        'cache':'purge',
        'execute': gdpr_database
    },
    'member-view-infractions': {
        'pretty_name': 'member-view-infractions',
        'description': 'Set whether members of the guild can view their own infraction count',
        'permission':'administrator',
        'cache':'keep',
        'execute': set_view_infractions
    },
    'set-prefix': {
        'pretty_name': 'set-prefix',
        'description': 'Set the Guild prefix',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': set_prefix
    },
    'set-muterole': {
        'pretty_name': 'set-muterole',
        'description': 'Set the mute role',
        'permission':'administrator',
        'cache':'keep',
        'execute': set_mute_role
    }
}
