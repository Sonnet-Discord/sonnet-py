# Reactionrole dlib for managing logic
# Ultrabear 2021

import importlib

import discord

import lib_loaders

importlib.reload(lib_loaders)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)

from lib_loaders import load_message_config, inc_statistics_better
from lib_lexdpyk_h import ToKernelArgs, KernelArgs

from typing import Dict, Any, Union, Optional, Tuple

reactionrole_types: Dict[Union[int, str], Any] = {0: "sonnet_reactionroles", "json": [["reaction-role-data", {}], ]}


def emojifrompayload(payload: discord.RawReactionActionEvent) -> Tuple[str, Optional[str]]:
    emoji = payload.emoji
    if emoji.is_unicode_emoji():
        return str(emoji.name), None
    elif emoji.is_custom_emoji():
        return str(emoji), str(emoji.id)
    else:
        return "", None


async def get_role_from_emojiname(payload: discord.RawReactionActionEvent, client: discord.Client, reactionroles: Dict[str, Dict[str, int]]) -> Optional[Tuple[discord.Member, discord.Role]]:

    emojiname, opt = emojifrompayload(payload)

    message_id_str = str(payload.message_id)

    if message_id_str not in reactionroles:
        return None

    if emojiname in reactionroles[message_id_str]:
        role_id = reactionroles[message_id_str][emojiname]
    elif opt is not None and opt in reactionroles[message_id_str]:
        role_id = reactionroles[message_id_str][opt]
    else:
        return None

    if not payload.guild_id:
        return None

    if (guild := (await client.fetch_guild(payload.guild_id))) and (member := (await guild.fetch_member(payload.user_id))) and (role := guild.get_role(role_id)):
        return member, role

    return None


@ToKernelArgs
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent, kargs: KernelArgs) -> None:

    if not payload.guild_id: return

    inc_statistics_better(payload.guild_id, "on-raw-reaction-add", kargs.kernel_ramfs)

    client: discord.Client = kargs.client
    rrconf: Optional[Dict[str, Dict[str, int]]] = load_message_config(payload.guild_id, kargs.ramfs, datatypes=reactionrole_types)["reaction-role-data"]

    if client.user:
        # do not give reactionroles to self
        if payload.user_id == client.user.id:
            return

    if rrconf:
        opt = await get_role_from_emojiname(payload, client, rrconf)
        if opt is not None:
            try:
                member, role = opt
                await member.add_roles(role)
            except discord.errors.Forbidden:
                pass


@ToKernelArgs
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent, kargs: KernelArgs) -> None:

    if not payload.guild_id: return

    inc_statistics_better(payload.guild_id, "on-raw-reaction-remove", kargs.kernel_ramfs)

    client: discord.Client = kargs.client
    rrconf: Optional[Dict[str, Dict[str, int]]] = load_message_config(payload.guild_id, kargs.ramfs, datatypes=reactionrole_types)["reaction-role-data"]

    if client.user:
        # do not remove reactionroles from self
        if payload.user_id == client.user.id:
            return

    if rrconf:
        opt = await get_role_from_emojiname(payload, client, rrconf)
        if opt is not None:
            try:
                member, role = opt
                await member.remove_roles(role)
            except discord.errors.Forbidden:
                pass


category_info = {'name': 'ReactionRoles'}

commands = {
    "on-raw-reaction-add": on_raw_reaction_add,
    "on-raw-reaction-remove": on_raw_reaction_remove,
    }

version_info = "2.0.0-DEV"
