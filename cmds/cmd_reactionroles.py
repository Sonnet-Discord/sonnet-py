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
from lib_parsers import parse_channel_message, message_parse_failure


async def add_reactionroles(message, args, client, **kwargs):

    try:
        rr_message, nargs = await parse_channel_message(message, args, client)
    except message_parse_failure:
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

    await message.channel.send(f"Added reactionrole to message id {rr_message.id}: {emoji}:{role.mention}", allowed_mentions=discord.AllowedMentions.none())


async def remove_reactionroles(message, args, client, **kwargs):
    await message.channel.send("Ultra needs to add this lolol")


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
    }

version_info = "1.1.5-DEV"
