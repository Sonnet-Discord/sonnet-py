# Moderation commands that focus on managing rather than immediate action
# Ultrabear 2022

import importlib

import discord, time, math, io, shlex

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)
import lib_parsers

importlib.reload(lib_parsers)
import lib_constants

importlib.reload(lib_constants)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)
import lib_tparse

importlib.reload(lib_tparse)
import lib_datetimeplus

importlib.reload(lib_datetimeplus)

from lib_loaders import load_embed_color, embed_colors
from lib_db_obfuscator import db_hlapi
from lib_parsers import format_duration, paginate_noexcept
from lib_sonnetconfig import REGEX_VERSION
from lib_sonnetcommands import CommandCtx
from lib_tparse import Parser
from lib_datetimeplus import Time
import lib_constants as constants

from typing import List, Tuple, Optional

# Import re to trick type checker into using re stubs
import re

# Import into globals hashmap to ignore pyflakes redefinition errors
globals()["re"] = importlib.import_module(REGEX_VERSION)


def get_user_id(s: str) -> int:
    return int(s.strip("<@!>"))


async def search_infractions_by_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    tstart = time.monotonic()

    if not ctx.verbose:
        raise lib_sonnetcommands.CommandError("ERROR: search-infractions only meant to be called directly")

    # Reparse args
    try:
        args = shlex.split(" ".join(args))
    except ValueError:
        raise lib_sonnetcommands.CommandError("ERROR: Shlex failed to parse arguments")

    # Parse flags
    parser = Parser("search-infractions")

    selected_chunk_f = parser.add_arg(["-p", "--page"], lambda s: int(s) - 1)
    responsible_mod_f = parser.add_arg(["-m", "--mod"], get_user_id)
    user_affected_f = parser.add_arg(["-u", "--user"], get_user_id)
    per_page_f = parser.add_arg(["-i", "--infractioncount"], int)
    infraction_type_f = parser.add_arg(["-t", "--type"], str)
    filtering_f = parser.add_arg(["-f", "--filter"], str)
    automod_f = lib_tparse.add_true_false_flag(parser, "automod")

    try:
        parser.parse(args, stderr=io.StringIO(), exit_on_fail=False, lazy=True)
    except lib_tparse.ParseFailureError:
        await message.channel.send("Failed to parse flags")
        return 1

    selected_chunk = selected_chunk_f.get(0)
    per_page = per_page_f.get(20)
    user_affected = user_affected_f.get()

    # Default to user if no user/mod flags are supplied
    if None is responsible_mod_f.get() is user_affected:
        try:
            user_affected = get_user_id(args[0])
        except (IndexError, ValueError):
            pass

    if not 1 <= per_page <= 40:  # pytype: disable=unsupported-operands
        await message.channel.send("ERROR: Cannot exceed range 1-40 infractions per page")
        return 1

    refilter: "Optional[re.Pattern[str]]"

    if (f := filtering_f.get()) is not None:
        try:
            refilter = re.compile(f)
        except re.error:
            raise lib_sonnetcommands.CommandError("ERROR: Filter regex is invalid")
    else:
        refilter = None

    with db_hlapi(message.guild.id) as db:
        if user_affected or responsible_mod_f.get():
            infractions = db.grab_filter_infractions(user=user_affected, moderator=responsible_mod_f.get(), itype=infraction_type_f.get(), automod=automod_f.get())
            assert isinstance(infractions, list)
        else:
            await message.channel.send("Please specify a user or moderator")
            return 1

    if refilter is not None:
        infractions = [i for i in infractions if refilter.findall(i[4])]

    # Sort newest first
    infractions.sort(reverse=True, key=lambda a: a[5])

    # Return if no infractions, this is not an error as it returned a valid status
    if not infractions:
        await message.channel.send("No infractions found")
        return 0

    cpagecount = math.ceil(len(infractions) / per_page)

    # Test if valid page
    if selected_chunk == -1:  # ik it says page 0 but it does -1 on user input so the user would have entered 0
        raise lib_sonnetcommands.CommandError("ERROR: Cannot go to page 0")
    elif selected_chunk < -1:
        selected_chunk = (cpagecount + selected_chunk) + 1

    def format_infraction(i: Tuple[str, str, str, str, str, int]) -> str:
        return ', '.join([i[0], i[3], i[4]])

    page = paginate_noexcept(infractions, selected_chunk, per_page, 1900, fmtfunc=format_infraction)

    tprint = (time.monotonic() - tstart) * 1000

    await message.channel.send(f"Page {selected_chunk+1} / {cpagecount} ({len(infractions)} infraction{'s'*(len(infractions)!=1)}) ({tprint:.1f}ms)\n```css\nID, Type, Reason\n{page}```")
    return 0


async def get_detailed_infraction(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if args:
        with db_hlapi(message.guild.id) as db:
            infraction = db.grab_infraction(args[0])
        if not infraction:
            await message.channel.send("ERROR: Infraction ID does not exist")
            return 1
    else:
        await message.channel.send("ERROR: No argument supplied")
        return 1

    # Unpack this nightmare lmao
    # pylint: disable=E0633
    infraction_id, user_id, moderator_id, infraction_type, reason, timestamp = infraction

    infraction_embed = discord.Embed(title="Infraction Search", description=f"Infraction for <@{user_id}>:", color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs))
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)

    infraction_embed.set_footer(text=f"uid: {user_id}, unix: {timestamp}")
    infraction_embed.timestamp = Time(unix=int(timestamp)).as_datetime()

    try:
        await message.channel.send(embed=infraction_embed)
        return 0
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def delete_infraction(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if args:
        with db_hlapi(message.guild.id) as db:
            infraction = db.grab_infraction(args[0])
            if not infraction:
                await message.channel.send("ERROR: Infraction ID does not exist")
                return 1
            # pylint: disable=E1136
            db.delete_infraction(infraction[0])
    else:
        await message.channel.send("ERROR: No argument supplied")
        return 1

    if not ctx.verbose:
        return 0

    # pylint: disable=E0633
    infraction_id, user_id, moderator_id, infraction_type, reason, timestamp = infraction

    infraction_embed = discord.Embed(title="Infraction Deleted", description=f"Infraction for <@{user_id}>:", color=load_embed_color(message.guild, embed_colors.deletion, ctx.ramfs))
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)

    infraction_embed.set_footer(text=f"uid: {user_id}, unix: {timestamp}")

    infraction_embed.timestamp = Time(unix=int(timestamp)).as_datetime()

    try:
        await message.channel.send(embed=infraction_embed)
        return 0
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


def notneg(v: int) -> int:
    if v < 0: raise ValueError
    return v


async def query_mutedb(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    parser = Parser("query_mutedb")
    pageP = parser.add_arg(["-p", "--page"], lambda s: notneg(int(s) - 1))

    try:
        parser.parse(args, stderr=io.StringIO(), exit_on_fail=False, lazy=True)
    except lib_tparse.ParseFailureError:
        raise lib_sonnetcommands.CommandError("Failed to parse page")

    page = pageP.get(0)

    per_page = 10

    with db_hlapi(message.guild.id) as db:
        table: List[Tuple[str, str, int]] = db.fetch_guild_mutes()

    if not table:
        await message.channel.send("No Muted users in database")
        return 0

    def fmtfunc(v: Tuple[str, str, int]) -> str:
        ts = "No Unmute" if v[2] == 0 else format_duration(v[2] - Time.now().unix())
        return (f"{v[1]}, {v[0]}, {ts}")

    out = paginate_noexcept(sorted(table, key=lambda i: i[2]), page, per_page, 1500, fmtfunc)

    await message.channel.send(f"Page {page+1} / {len(table)//per_page+1}, ({len(table)} mute{'s'*(len(table)!=1)})```css\nUid, InfractionID, Unmuted in\n{out}```")
    return 0


async def remove_mutedb(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    try:
        uid = int(args[0].strip("<@!>"))
    except ValueError:
        await message.channel.send("ERROR: Invalid user")
        return 1
    except IndexError:
        await message.channel.send("ERROR: No user specified")
        return 1

    with db_hlapi(message.guild.id) as db:
        if db.is_muted(userid=uid):
            db.unmute_user(userid=uid)

            await message.channel.send("Removed user from mute database")

        else:
            await message.channel.send("ERROR: User is not in mute database")
            return 1

    return 0


category_info = {'name': 'bookkeeping', 'pretty_name': 'Bookkeeping', 'description': 'Commands to assist with moderation bookkeeping'}

commands = {
    'remove-mute': {
        'pretty_name': 'remove-mute <user>',
        'description': 'Removes a user from the mute database. Does not unmute in guild',
        'permission': 'administrator',
        'execute': remove_mutedb,
        },
    'list-mutes': {
        'pretty_name': 'list-mutes [-p PAGE]',
        'description': 'List all mutes in the mute database',
        'permission': 'moderator',
        'execute': query_mutedb,
        },
    'warnings': {
        'alias': 'search-infractions'
        },
    'list-infractions': {
        'alias': 'search-infractions'
        },
    'infractions': {
        'alias': 'search-infractions'
        },
    'search-infractions':
        {
            'pretty_name': 'search-infractions <-u USER | -m MOD> [-t TYPE] [-p PAGE] [-i INF PER PAGE] [--[no-]automod] [-f FILTER]',
            'description': 'Grab infractions of a user, -f uses regex',
            'rich_description': 'Supports negative indexing in pager, flags are unix like',
            'permission': 'moderator',
            'execute': search_infractions_by_user
            },
    'get-infraction': {
        'alias': 'infraction-details'
        },
    'grab-infraction': {
        'alias': 'infraction-details'
        },
    'infraction-details': {
        'pretty_name': 'infraction-details <infractionID>',
        'description': 'Grab details of an infractionID',
        'permission': 'moderator',
        'execute': get_detailed_infraction
        },
    'remove-infraction': {
        'alias': 'delete-infraction'
        },
    'rm-infraction': {
        'alias': 'delete-infraction'
        },
    'delete-infraction': {
        'pretty_name': 'delete-infraction <infractionID>',
        'description': 'Delete an infraction by infractionID',
        'permission': 'administrator',
        'execute': delete_infraction
        },
    }

version_info: str = "1.2.13-DEV"
