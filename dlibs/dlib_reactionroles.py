# Reactionrole dlib for managing logic
# Ultrabear 2021

import importlib

import discord
import json

import lib_loaders
importlib.reload(lib_loaders)

from lib_loaders import load_message_config, inc_statistics

reactionrole_types = {0: "sonnet_reactionroles", "csv": [], "text": [["reaction-role-data", ""], ]}


async def on_raw_reaction_add(payload, **kargs):

    if not payload.guild_id: return

    inc_statistics([payload.guild_id, "on-raw-reaction-add", kargs["kernel_ramfs"]])

    client = kargs["client"]
    rrconf = load_message_config(payload.guild_id, kargs["ramfs"], datatypes=reactionrole_types)["reaction-role-data"]

    if rrconf:
        rrconf = json.loads(rrconf)
        if str(payload.message_id) in rrconf and payload.emoji.name in rrconf[str(payload.message_id)]:
            role_id = rrconf[str(payload.message_id)][payload.emoji.name]
            if (guild := (await client.fetch_guild(payload.guild_id))) and (member := (await guild.fetch_member(payload.user_id))) and (role := guild.get_role(role_id)):
                try:
                    await member.add_roles(role)
                except discord.errors.Forbidden:
                    pass


async def on_raw_reaction_remove(payload, **kargs):

    if not payload.guild_id: return

    inc_statistics([payload.guild_id, "on-raw-reaction-remove", kargs["kernel_ramfs"]])

    client = kargs["client"]
    rrconf = load_message_config(payload.guild_id, kargs["ramfs"], datatypes=reactionrole_types)["reaction-role-data"]

    if rrconf:
        rrconf = json.loads(rrconf)
        if str(payload.message_id) in rrconf and payload.emoji.name in rrconf[str(payload.message_id)]:
            role_id = rrconf[str(payload.message_id)][payload.emoji.name]
            if (guild := (await client.fetch_guild(payload.guild_id))) and (member := (await guild.fetch_member(payload.user_id))) and (role := guild.get_role(role_id)):
                try:
                    await member.remove_roles(role)
                except discord.errors.Forbidden:
                    pass


category_info = {'name': 'ReactionRoles'}

commands = {
    "on-raw-reaction-add": on_raw_reaction_add,
    "on-raw-reaction-remove": on_raw_reaction_remove,
    }

version_info = "1.1.5"
