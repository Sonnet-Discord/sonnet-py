# User update tracking
# Ultrabear 2021

import importlib

import discord, time, asyncio
from datetime import datetime

import lib_loaders

importlib.reload(lib_loaders)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)

from lib_loaders import inc_statistics_better, load_embed_color, embed_colors, load_message_config

from typing import Any, Dict, Union, List
import lib_lexdpyk_h as lexdpyk


async def catch_logging_error(channel: discord.TextChannel, embed: discord.Embed) -> None:
    try:
        await channel.send(embed=embed)
    except discord.errors.Forbidden:
        pass


join_leave_user_logs: Dict[Union[str, int], Union[str, List[List[Any]]]] = {0: "sonnet_userupdate_log", "text": [["username-log", ""], ["join-log", ""], ["leave-log", ""]]}


async def on_member_update(before: discord.Member, after: discord.Member, **kargs: Any) -> None:

    inc_statistics_better(before.guild.id, "on-member-update", kargs["kernel_ramfs"])

    username_log = load_message_config(before.guild.id, kargs["ramfs"], datatypes=join_leave_user_logs)["username-log"]

    if username_log and (channel := kargs["client"].get_channel(int(username_log))):
        if before.nick == after.nick:
            return

        message_embed = discord.Embed(title="Nickname updated", color=load_embed_color(before.guild, embed_colors.edit, kargs["ramfs"]))
        message_embed.set_author(name=f"{before} ({before.id})", icon_url=before.avatar_url)
        message_embed.add_field(name="Before" + " | False" * (not bool(before.nick)), value=before.nick)
        message_embed.add_field(name="After" + " | False" * (not bool(after.nick)), value=after.nick)

        message_embed.timestamp = datetime.utcnow()
        message_embed.set_footer(text=f"unix: {int(datetime.utcnow().timestamp())}")

        await catch_logging_error(channel, message_embed)


def parsedate(indata: datetime) -> str:
    return f"{time.strftime('%a, %d %b %Y %H:%M:%S', indata.utctimetuple())} ({(datetime.utcnow() - indata).days} days ago)"


join_notifier: Dict[Union[str, int], Union[str, List[List[Any]]]] = {
    0: 'sonnet_join_notifier',
    "json": [["notifier-log-users", []], ],
    "text": [["notifier-log-timestamp", "0"], ["notifier-log-defaultpfp", "0"], ["regex-notifier-log", ""]],
    }


async def notify_problem(member: discord.Member, ptype: List[str], log: str, client: discord.Client, ramfs: lexdpyk.ram_filesystem) -> None:

    if log and (channel := client.get_channel(int(log))):

        notify_embed = discord.Embed(title=f"Notify on member join: {member}", description=f"Notifying for: {', '.join(ptype)}", color=load_embed_color(member.guild, embed_colors.primary, ramfs))
        notify_embed.set_footer(text=f"uid: {member.id}")

        try:
            await channel.send(embed=notify_embed)
        except discord.errors.Forbidden:
            pass


async def on_member_join(member: discord.Member, **kargs: Any) -> None:

    inc_statistics_better(member.guild.id, "on-member-join", kargs["kernel_ramfs"])

    notifier_cache = load_message_config(member.guild.id, kargs["ramfs"], datatypes=join_notifier)

    issues: List[str] = []

    if member.id in notifier_cache["notifier-log-users"]:
        issues.append("User")
    if abs(datetime.utcnow().timestamp() - member.created_at.timestamp()) < int(notifier_cache["notifier-log-timestamp"]):
        issues.append("Timestamp")
    if int(notifier_cache["notifier-log-defaultpfp"]) and member.avatar_url == member.default_avatar_url:
        issues.append("Default pfp")

    if issues:
        asyncio.create_task(notify_problem(member, issues, notifier_cache["regex-notifier-log"], kargs["client"], kargs["ramfs"]))

    joinlog = load_message_config(member.guild.id, kargs["ramfs"], datatypes=join_leave_user_logs)["join-log"]

    if joinlog and (logging_channel := kargs["client"].get_channel(int(joinlog))):

        embed = discord.Embed(title=f"{member} joined.", description=f"*{member.mention} joined the server.*", color=load_embed_color(member.guild, embed_colors.creation, kargs["ramfs"]))
        embed.set_thumbnail(url=member.avatar_url)

        embed.timestamp = datetime.utcnow()
        embed.set_footer(text=f"uid: {member.id}, unix: {int(discord.utils.utcnow().timestamp())}")

        embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)

        await catch_logging_error(logging_channel, embed)


async def on_member_remove(member: discord.Member, **kargs: Any) -> None:

    inc_statistics_better(member.guild.id, "on-member-remove", kargs["kernel_ramfs"])

    log_channels = load_message_config(member.guild.id, kargs["ramfs"], datatypes=join_leave_user_logs)

    if (joinlog := (log_channels["leave-log"] or log_channels["join-log"])):
        if logging_channel := kargs["client"].get_channel(int(joinlog)):

            embed = discord.Embed(title=f"{member} left.", description=f"*{member.mention} left the server.*", color=load_embed_color(member.guild, embed_colors.deletion, kargs["ramfs"]))
            embed.set_thumbnail(url=member.avatar_url)

            embed.timestamp = datetime.utcnow()
            embed.set_footer(text=f"uid: {member.id}, unix: {int(datetime.utcnow().timestamp())}")

            embed.add_field(name="Created", value=parsedate(member.created_at), inline=True)
            embed.add_field(name="Joined", value=parsedate(member.joined_at), inline=True)

            await catch_logging_error(logging_channel, embed)


category_info = {'name': 'UserUpdate'}

commands = {
    "on-member-update": on_member_update,
    "on-member-join": on_member_join,
    "on-member-remove": on_member_remove,
    }

version_info: str = "pre2.0.0-DEV"
