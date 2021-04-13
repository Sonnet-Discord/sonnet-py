# Reactionroles settings
# Ultrabear 2021

import importlib

import discord
import json, io

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)

from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_channel_message


class InvalidEmoji(Exception):
    pass


async def valid_emoji(message, pEmoji, client):

    if len(pEmoji) == 1:
        return pEmoji
    else:

        try:
            em = int(pEmoji.split(":")[-1].rstrip(">"))
        except ValueError:
            await message.channel.send("ERROR: Could not validate emoji")
            raise InvalidEmoji

        em = client.get_emoji(em)

        if not em:
            await message.channel.send("ERROR: Emoji does not exist in scope")
            raise InvalidEmoji

        return str(em)


class RindexFailure(Exception):
    pass


async def rindex_check(message, role):

    rindex = message.guild.roles.index(role)

    if rindex >= message.guild.roles.index(message.author.roles[-1]):
        await message.channel.send("Cannot autorole a role that is higher or the same as your current top role")
        raise RindexFailure
    elif rindex >= message.guild.roles.index(message.guild.me.roles[-1]):
        await message.channel.send("Cannot autorole a role that is higher or the same as this bots top role")
        raise RindexFailure


async def add_reactionroles(message, args, client, **kwargs):

    try:
        rr_message, nargs = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    args = args[nargs:]

    if len(args) < 2:
        await message.channel.send("Not enough args supplied")
        return 1

    try:
        emoji = await valid_emoji(message, args[0], client)
    except InvalidEmoji:
        return 1

    role = args[1].strip("<@&>")

    try:
        role = message.guild.get_role(int(role))
    except ValueError:
        await message.channel.send("Invalid role")
        return 1

    if not role:
        await message.channel.send("Invalid role")
        return 1

    try:
        await rindex_check(message, role)
    except RindexFailure:
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles = db.grab_config("reaction-role-data")

    if reactionroles:
        reactionroles = json.loads(reactionroles)
    else:
        reactionroles = {}

    if str(rr_message.id) in reactionroles:
        reactionroles[str(rr_message.id)][emoji] = role.id
    else:
        reactionroles[str(rr_message.id)] = {}
        reactionroles[str(rr_message.id)][emoji] = role.id

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Added reactionrole to message id {rr_message.id}: {emoji}:{role.mention}", allowed_mentions=discord.AllowedMentions.none())


async def remove_reactionroles(message, args, client, **kwargs):

    try:
        rr_message, nargs = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    args = args[nargs:]

    if not args:
        await message.channel.send("Not enough args supplied")
        return 1

    try:
        emoji = await valid_emoji(message, args[0], client)
    except InvalidEmoji:
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles = db.grab_config("reaction-role-data")

    if not reactionroles:
        await message.channel.send("ERROR: This guild has no reactionroles")
        return 1

    reactionroles = json.loads(reactionroles)

    if str(rr_message.id) in reactionroles:
        if emoji in reactionroles[str(rr_message.id)]:
            del reactionroles[str(rr_message.id)][emoji]
        else:
            await message.channel.send(f"This message does not have {emoji} reactionrole on it")
            return 1
    else:
        await message.channel.send("This message has no reactionroles on it")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Removed reactionrole {emoji} from message id {rr_message.id}")


async def list_reactionroles(message, args, client, **kwargs):

    with db_hlapi(message.guild.id) as db:
        data = json.loads(db.grab_config("reaction-role-data") or "{}")

    reactionrole_embed = discord.Embed(title=f"ReactionRoles in {message.guild}")

    if data:

        if len(data) <= 25:
            for i in data:
                reactionrole_embed.add_field(name=i, value="\n".join([f"{emoji}: <@&{data[i][emoji]}>" for emoji in data[i]]))

            await message.channel.send(embed=reactionrole_embed)

        else:

            fileobj = io.BytesIO()
            fileobj.write(json.dumps(data).encode("utf8"))
            fileobj.seek(0)
            dfile = discord.File(fileobj, filename="RR.json")
            await message.channel.send("Too many rr messages to send in embed", file=dfile)

    else:
        await message.channel.send("This guild has no reactionroles")


async def addmany_reactionroles(message, args, client, **kwargs):

    try:
        rr_message, nargs = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    args = args[nargs:]

    with db_hlapi(message.guild.id) as db:
        reactionroles = json.loads(db.grab_config("reaction-role-data") or "{}")

    for i in range(len(args) // 2):
        try:
            emoji = await valid_emoji(message, args[i * 2], client)
        except InvalidEmoji:
            return 1
        role = args[i * 2 + 1].strip("<@&>")

        try:
            role = message.guild.get_role(int(role))
        except ValueError:
            await message.channel.send("Invalid role")
            return 1

        if not role:
            await message.channel.send("Invalid role")
            return 1

        try:
            await rindex_check(message, role)
        except RindexFailure:
            return 1

        if str(rr_message.id) in reactionroles:
            reactionroles[str(rr_message.id)][emoji] = role.id
        else:
            reactionroles[str(rr_message.id)] = {}
            reactionroles[str(rr_message.id)][emoji] = role.id

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send("Added Multiple reactionroles")


async def rr_purge(message, args, client, **kwargs):

    try:
        message_id = int(args[0].replace("-", "/").split("/")[-1])
    except IndexError:
        await message.channel.send("ERROR: No message id supplied")
        return 1
    except ValueError:
        await message.channel.send("ERROR: Message id is not a valid int")
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles = db.grab_config("reaction-role-data")

    if not reactionroles:
        await message.channel.send("ERROR: This guild has no reactionroles")
        return 1

    reactionroles = json.loads(reactionroles)

    if str(message_id) in reactionroles:
        del reactionroles[str(message_id)]
    else:
        await message.channel.send("ERROR: This message has no reactionroles")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Purged reactionroles from message with id {message_id}")


category_info = {'name': 'rr', 'pretty_name': 'Reaction Roles', 'description': 'Commands for controlling Reaction Role settings'}

commands = {
    'rr-add': {
        'pretty_name': 'rr-add <message> <emoji> <role>',
        'description': 'Add a reactionrole to a message',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': add_reactionroles
        },
    'rr-purge':
        {
            'pretty_name': 'rr-purge <message id>',
            'description': 'Purge all reactionroles from a message',
            'rich_description': 'Currently the only way to remove reactionroles from a deleted message',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': rr_purge
            },
    'rr-remove':
        {
            'pretty_name': 'rr-remove <message> <emoji>',
            'description': 'Remove a reactionrole from a message',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': remove_reactionroles
            },
    'rr-list':
        {
            'pretty_name': 'rr-list',
            'description': 'List all reactionroles in guild',
            'rich_description': 'Does not display in guilds with more than 25 messages, will instead drop a file',
            'permission': 'administrator',
            'cache': 'keep',
            'execute': list_reactionroles
            },
    'rr-addmany':
        {
            'pretty_name': 'rr-addmany <message> (?:<emoji> <role>)+',
            'description': 'Add multiple reactionroles',
            'rich_description': 'Multiple reactionroles can be space or newline seperated',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': addmany_reactionroles
            },
    }

version_info = "1.2.3-DEV"
