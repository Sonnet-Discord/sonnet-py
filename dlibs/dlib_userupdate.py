# User update tracking
# Ultrabear 2021

import asyncio
from datetime import datetime

import discord

from typing import Any, Dict, List, Optional, Union

import lib_lexdpyk_h as lexdpyk
from lib_compatibility import (discord_datetime_now, has_default_avatar, user_avatar_url, to_snowflake)
from lib_db_obfuscator import db_hlapi
from lib_loaders import (datetime_now, embed_colors, inc_statistics_better, load_embed_color, load_message_config)
from lib_parsers import parse_boolean_strict
from lib_sonnetconfig import AUTOMOD_ENABLED


async def catch_logging_error(channel: discord.TextChannel, embed: discord.Embed) -> None:
    try:
        await channel.send(embed=embed)
    except discord.errors.Forbidden:
        pass


join_leave_user_logs: Dict[Union[str, int], Union[str, List[List[Any]]]] = {
    0: "sonnet_userupdate_log",
    "text": [["username-log", ""], ["join-log", ""], ["leave-log", ""], ["leave-log-is-join-log", "1"]]
    }


async def on_member_update(before: discord.Member, after: discord.Member, **kargs: Any) -> None:

    inc_statistics_better(before.guild.id, "on-member-update", kargs["kernel_ramfs"])

    username_log = load_message_config(before.guild.id, kargs["ramfs"], datatypes=join_leave_user_logs)["username-log"]

    if username_log and (channel := kargs["client"].get_channel(int(username_log))):
        if before.nick == after.nick:
            return

        def nick_or_unset(s: Optional[str]) -> str:
            if s is None:
                return "_ _"
            return s

        message_embed = discord.Embed(title="Nickname updated", color=load_embed_color(before.guild, embed_colors.edit, kargs["ramfs"]))
        message_embed.set_author(name=f"{before} ({before.id})", icon_url=user_avatar_url(before))
        message_embed.add_field(name=("Before" + " (Not set)" * (not before.nick)), value=nick_or_unset(before.nick))
        message_embed.add_field(name=("After" + " (Not set)" * (not after.nick)), value=nick_or_unset(after.nick))

        message_embed.timestamp = ts = datetime_now()
        message_embed.set_footer(text=f"unix: {int(ts.timestamp())}")

        await catch_logging_error(channel, message_embed)


def parsedate(indata: Optional[datetime]) -> str:
    if indata is not None:
        basetime = format(indata, '%a, %d %b %Y %H:%M:%S')
        days = (discord_datetime_now() - indata).days
        return f"{basetime} ({days} day{'s' * (days != 1)} ago)"
    else:
        return "ERROR: Could not fetch this date"


join_notifier: Dict[Union[str, int], Union[str, List[List[Any]]]] = {
    0: 'sonnet_join_notifier',
    "json": [["notifier-log-users", []], ],
    "text": [["notifier-log-timestamp", "0"], ["notifier-log-defaultpfp", "0"], ["regex-notifier-log", ""]],
    }


# Notify on member join for red flags
async def notify_problem(member: discord.Member, ptype: List[str], log: str, client: discord.Client, ramfs: lexdpyk.ram_filesystem) -> None:

    if log and (channel := client.get_channel(int(log))):

        if not isinstance(channel, discord.TextChannel):
            return

        notify_embed = discord.Embed(title=f"Notify on member join: {member}", description=f"Notifying for: {', '.join(ptype)}", color=load_embed_color(member.guild, embed_colors.primary, ramfs))
        notify_embed.set_footer(text=f"uid: {member.id}")

        await catch_logging_error(channel, notify_embed)


async def try_mute_on_rejoin(member: discord.Member, db: db_hlapi, client: discord.Client, log: str, ramfs: lexdpyk.ram_filesystem) -> None:

    mute_role_id = db.grab_config("mute-role")
    if mute_role_id and (mute_role := member.guild.get_role(int(mute_role_id))):

        success: bool

        try:
            await member.add_roles(to_snowflake(mute_role))
            success = True
        except discord.errors.Forbidden:
            success = False

        stringcases = {
            False: "was not able to be remuted (permissions error)",
            True: "was remuted",
            }

        if log and (channel := client.get_channel(int(log))):
            if isinstance(channel, discord.TextChannel):

                muted_embed = discord.Embed(
                    title=f"Notify on muted member join: {member}",
                    description=f"This user has an entry in the mute database and {stringcases[success]}.",
                    color=load_embed_color(member.guild, embed_colors.primary, ramfs)
                    )
                muted_embed.set_footer(text=f"uid: {member.id}")

                await catch_logging_error(channel, muted_embed)


# Handles join logs and regex joinnotifier
async def on_member_join(member: discord.Member, **kargs: Any) -> None:

    client: discord.Client = kargs["client"]
    ramfs: lexdpyk.ram_filesystem = kargs["ramfs"]

    inc_statistics_better(member.guild.id, "on-member-join", kargs["kernel_ramfs"])

    notifier_cache = load_message_config(member.guild.id, ramfs, datatypes=join_notifier)

    issues: List[str] = []

    if AUTOMOD_ENABLED:
        # Handle notifier logging
        if member.id in notifier_cache["notifier-log-users"]:
            issues.append("User")
        if abs(discord_datetime_now().timestamp() - member.created_at.timestamp()) < int(notifier_cache["notifier-log-timestamp"]):
            issues.append("Timestamp")
        if int(notifier_cache["notifier-log-defaultpfp"]) and has_default_avatar(member):
            issues.append("Default pfp")

        if issues:
            asyncio.create_task(notify_problem(member, issues, notifier_cache["regex-notifier-log"], client, ramfs))

    joinlog = load_message_config(member.guild.id, ramfs, datatypes=join_leave_user_logs)["join-log"]

    # Handle join logs
    if joinlog and (logging_channel := client.get_channel(int(joinlog))):

        embed = discord.Embed(title=f"{member} joined.", description=f"*{member.mention} joined the server.*", color=load_embed_color(member.guild, embed_colors.creation, ramfs))
        embed.set_thumbnail(url=user_avatar_url(member))

        embed.timestamp = ts = datetime_now()
        embed.set_footer(text=f"uid: {member.id}, unix: {int(ts.timestamp())}")

        embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)

        if isinstance(logging_channel, discord.TextChannel):
            asyncio.create_task(catch_logging_error(logging_channel, embed))

    with db_hlapi(member.guild.id) as db:
        if db.is_muted(userid=member.id):
            await try_mute_on_rejoin(member, db, client, notifier_cache["regex-notifier-log"], ramfs)


# Handles member leave logging
async def on_member_remove(member: discord.Member, **kargs: Any) -> None:

    inc_statistics_better(member.guild.id, "on-member-remove", kargs["kernel_ramfs"])

    log_channels = load_message_config(member.guild.id, kargs["ramfs"], datatypes=join_leave_user_logs)

    # Try for leave-log, default to join-log if leave-log-is-join-log is set
    if joinlog := (log_channels["leave-log"] or (log_channels["join-log"] if parse_boolean_strict(log_channels["leave-log-is-join-log"]) else None)):
        if logging_channel := kargs["client"].get_channel(int(joinlog)):

            # Only run if in a TextChannel
            if not isinstance(logging_channel, discord.TextChannel):
                return

            embed = discord.Embed(title=f"{member} left.", description=f"*{member.mention} left the server.*", color=load_embed_color(member.guild, embed_colors.deletion, kargs["ramfs"]))
            embed.set_thumbnail(url=user_avatar_url(member))

            embed.timestamp = ts = datetime_now()
            embed.set_footer(text=f"uid: {member.id}, unix: {int(ts.timestamp())}")

            embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)
            embed.add_field(name="Joined", value=parsedate(member.joined_at), inline=True)

            await catch_logging_error(logging_channel, embed)


category_info = {'name': 'UserUpdate'}

commands = {
    "on-member-update": on_member_update,
    "on-member-join": on_member_join,
    "on-member-remove": on_member_remove,
    }

version_info: str = "2.0.1"
