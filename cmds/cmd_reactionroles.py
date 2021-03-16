# Reactionroles settings
# Ultrabear 2021

import importlib

import discord
import json

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_parsers
importlib.reload(lib_parsers)

from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_channel_message


async def add_reactionroles(message, args, client, **kwargs):

    try:
        rr_message, nargs = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return

    args = args[nargs:]

    if len(args) < 2:
        await message.channel.send("Not enough args supplied")
        return

    emoji = args[0]

    role = args[1].strip("<@&>")

    try:
        role = message.guild.get_role(int(role))
    except ValueError:
        await message.channel.send("Invalid role")
        return

    if not role:
        await message.channel.send("Invalid role")
        return

    rindex = message.guild.roles.index(role)

    if rindex >= message.guild.roles.index(message.author.roles[-1]):
        await message.channel.send("Cannot autorole a role that is higher or the same as your current top role")
        return
    elif rindex >= message.guild.roles.index(message.guild.me.roles[-1]):
        await message.channel.send("Cannot autorole a role that is higher or the same as this bots top role")
        return

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
        return

    args = args[nargs:]

    if not args:
        await message.channel.send("Not enough args supplied")
        return

    emoji = args[0]

    with db_hlapi(message.guild.id) as db:
        reactionroles = db.grab_config("reaction-role-data")

    if not reactionroles:
        await message.channel.send("ERROR: This guild has no reactionroles")
        return

    reactionroles = json.loads(reactionroles)

    if str(rr_message.id) in reactionroles:
        if emoji in reactionroles[str(rr_message.id)]:
            del reactionroles[str(rr_message.id)][emoji]
        else:
            await message.channel.send(f"This message does not have {emoji} reactionrole on it")
            return
    else:
        await message.channel.send("This message has no reactionroles on it")
        return

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Removed reactionrole {emoji} from message id {rr_message.id}")


async def list_reactionroles(message, args, client, **kwargs):

    with db_hlapi(message.guild.id) as db:
        data = json.loads(db.grab_config("reaction-role-data") or "{}")

    reactionrole_embed = discord.Embed(title=f"ReactionRoles in {message.guild}")

    for i in data:
        reactionrole_embed.add_field(name=i, value="\n".join([f"{emoji}: <@&{data[i][emoji]}>" for emoji in data[i]]))

    try:
        await message.channel.send(embed=reactionrole_embed)
    except discord.errors.HTTPException:
        await message.channel.send("Too many messages to display")


category_info = {'name': 'rr', 'pretty_name': 'Reaction Roles', 'description': 'Commands for controlling Reaction Role settings'}

commands = {
    'rr-add': {
        'pretty_name': 'rr-add <message> <emoji> <role>',
        'description': 'Add a reactionrole to a message',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': add_reactionroles
        },
    'rr-remove':
        {
            'pretty_name': 'rr-remove <message> <emoji>',
            'description': 'Remove a reactionrole from a message',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': remove_reactionroles
            },
    'rr-list': {
        'pretty_name': 'rr-list',
        'description': 'List all reactionroles in guild',
        'permission': 'administrator',
        'cache': 'keep',
        'execute': list_reactionroles
        },
    }

version_info = "1.1.6-DEV"
