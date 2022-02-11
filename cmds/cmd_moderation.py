# Moderation commands
# bredo, 2020

import importlib

import discord, time, asyncio, math, io, shlex, json
from dataclasses import dataclass

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)
import lib_parsers

importlib.reload(lib_parsers)
import lib_constants

importlib.reload(lib_constants)
import lib_goparsers

importlib.reload(lib_goparsers)
import lib_compatibility

importlib.reload(lib_compatibility)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)
import lib_tparse

importlib.reload(lib_tparse)

from lib_goparsers import MustParseDuration
from lib_loaders import generate_infractionid, load_embed_color, embed_colors, datetime_now, datetime_unix
from lib_db_obfuscator import db_hlapi
from lib_parsers import grab_files, generate_reply_field, parse_channel_message_noexcept, parse_user_member, format_duration, paginate_noexcept
from lib_compatibility import user_avatar_url
from lib_sonnetconfig import BOT_NAME, REGEX_VERSION
from lib_sonnetcommands import CommandCtx
from lib_tparse import Parser
import lib_constants as constants

from typing import List, Tuple, Awaitable, Optional, Callable, Union, Final, Dict, cast
import lib_lexdpyk_h as lexdpyk

# Import re to trick type checker into using re stubs
import re

# Import into globals hashmap to ignore pyflakes redefinition errors
globals()["re"] = importlib.import_module(REGEX_VERSION)


# Catches error if the bot cannot message the user
async def catch_dm_error(user: Union[discord.User, discord.Member], contents: discord.Embed, log_channel: Optional[discord.TextChannel]) -> None:
    try:
        await user.send(embed=contents)
    except (AttributeError, discord.errors.HTTPException):
        if log_channel is not None:
            try:
                asyncio.create_task(log_channel.send(f"ERROR: {user.mention}:{user.id} Could not DM user", allowed_mentions=discord.AllowedMentions.none()))
            except discord.errors.Forbidden:
                pass


async def catch_logging_error(embed: discord.Embed, log_channel: discord.TextChannel) -> None:
    try:
        await log_channel.send(embed=embed)
    except discord.errors.Forbidden:
        try:
            await log_channel.send(constants.sonnet.error_embed)
        except discord.errors.Forbidden:
            pass


# Defines an error that somehow log_infraction was called without a guild
# Should never really happen so its a easter egg now ig
class GuildScopeError(Exception):
    __slots__ = ()


InterfacedUser = Union[discord.User, discord.Member]


@dataclass
class InfractionModifier:
    __slots__ = "key", "title", "value"
    key: str
    title: str
    value: str

    def store_in(self, e: discord.Embed) -> None:
        e.add_field(name=self.title, value=self.value)


# Sends an infraction to database and log channels if user exists
async def log_infraction(
    message: discord.Message, client: discord.Client, user: InterfacedUser, moderator: InterfacedUser, i_reason: str, i_type: str, to_dm: bool, ramfs: lexdpyk.ram_filesystem,
    modifiers: List[InfractionModifier]
    ) -> Tuple[str, Optional[Awaitable[None]]]:
    if not message.guild:
        raise GuildScopeError("How did we even get here")

    timestamp = datetime_now()  # Infraction timestamp

    # Define db outputs scoped correctly
    generated_id: str
    log_channel: Optional[discord.TextChannel]

    with db_hlapi(message.guild.id) as db:

        # Infraction id collision test
        while db.grab_infraction(generated_id := generate_infractionid()):
            continue

        # Grab log channel
        try:
            chan: int = int(db.grab_config("infraction-log") or "0")
        except ValueError:
            chan = 0

        c = client.get_channel(chan)
        log_channel = c if isinstance(c, discord.TextChannel) else None

        # Send infraction to database
        db.add_infraction(generated_id, str(user.id), str(moderator.id), i_type, i_reason, int(timestamp.timestamp()))

    if log_channel:

        log_embed = discord.Embed(title=BOT_NAME, description=f"New infraction for {user}:", color=load_embed_color(message.guild, embed_colors.creation, ramfs))
        log_embed.set_thumbnail(url=user_avatar_url(user))
        log_embed.add_field(name="Infraction ID", value=generated_id)
        log_embed.add_field(name="Moderator", value=moderator.mention)
        log_embed.add_field(name="User", value=user.mention)
        log_embed.add_field(name="Type", value=i_type)
        log_embed.add_field(name="Reason", value=i_reason)

        if modifiers:
            log_embed.add_field(name="Modifiers", value=' '.join(f"+{m.key}" for m in modifiers))

        log_embed.set_footer(text=f"uid: {user.id}, unix: {int(timestamp.timestamp())}")

        asyncio.create_task(catch_logging_error(log_embed, log_channel))

    if not to_dm:
        return generated_id, None

    dm_embed = discord.Embed(title=BOT_NAME, description=f"You received an infraction in {message.guild.name}:", color=load_embed_color(message.guild, embed_colors.primary, ramfs))
    dm_embed.set_thumbnail(url=user_avatar_url(user))
    dm_embed.add_field(name="Infraction ID", value=str(generated_id))
    dm_embed.add_field(name="Type", value=i_type)
    dm_embed.add_field(name="Reason", value=i_reason)

    for i in modifiers:
        i.store_in(dm_embed)

    dm_embed.timestamp = timestamp

    dm_sent = asyncio.create_task(catch_dm_error(user, dm_embed, log_channel))

    return (generated_id, dm_sent)


class InfractionGenerationError(Exception):
    __slots__ = ()


InfractionInfo = Tuple[Optional[discord.Member], InterfacedUser, str, str, Optional[Awaitable[None]]]


# General processor for infractions
async def process_infraction(
    message: discord.Message,
    args: List[str],
    client: discord.Client,
    i_type: str,
    ramfs: lexdpyk.ram_filesystem,
    infraction: bool = True,
    automod: bool = False,
    modifiers: Optional[List[InfractionModifier]] = None
    ) -> InfractionInfo:
    if not message.guild or not isinstance(message.author, discord.Member):
        raise InfractionGenerationError("User is not member, or no guild")

    reason: str = " ".join(args[1:])[:1024] if len(args) > 1 else "No Reason Specified"

    # Potential BUG: discord.abc.User != discord.user.User under mypy
    # Due to this we have to cast
    moderator = cast(discord.User, client.user if automod else message.author)

    # Test if user is valid
    try:
        user, member = await parse_user_member(message, args, client)
    except lib_parsers.errors.user_parse_error:
        raise InfractionGenerationError("Could not parse user")

    # Test if user is self
    if member and moderator.id == member.id:
        await message.channel.send(f"Cannot {i_type} yourself")
        raise InfractionGenerationError(f"Attempted self {i_type}")

    # Do a permission sweep
    if not automod and member and message.guild.roles.index(message.author.roles[-1]) <= message.guild.roles.index(member.roles[-1]):
        await message.channel.send(f"Cannot {i_type} a user with the same or higher role as yourself")
        raise InfractionGenerationError(f"Attempted nonperm {i_type}")

    modifiers = [] if modifiers is None else modifiers

    # bound modifiers to max of 3 (prevents embed size overflow)
    modlimit: Final = 3
    if len(modifiers) > modlimit:
        await message.channel.send(f"Too many infraction modifiers passed (limit {modlimit}, given {len(modifiers)})")
        raise InfractionGenerationError("Too many modifiers")

    # Log infraction
    infraction_id, dm_sent = await log_infraction(message, client, user, moderator, reason, i_type, infraction, ramfs, modifiers)

    return (member, user, reason, infraction_id, dm_sent)


InfracModifierDBT = Dict[str, Tuple[str, str]]


def parse_infraction_modifiers(guild: discord.Guild, args: List[str]) -> List[InfractionModifier]:

    if len(args) >= 2 and args[0].startswith("+"):
        modifiers = args.pop(0)[1:].split(',')

        mlist: List[InfractionModifier] = []

        with db_hlapi(guild.id) as db:
            data: InfracModifierDBT = json.loads(db.grab_config("infraction-modifiers") or "{}")
            for i in modifiers:
                if i in data:
                    mlist.append(InfractionModifier(i, data[i][0], data[i][1]))
                else:
                    raise lib_sonnetcommands.CommandError("ERROR: No infraction modifier with name specified")

        return mlist

    return []


async def warn_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    modifiers = parse_infraction_modifiers(message.guild, args)

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "warn", ctx.ramfs, automod=ctx.automod, modifiers=modifiers)
    except InfractionGenerationError:
        return 1

    if ctx.verbose and user:
        await message.channel.send(f"Warned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1

    return 0


async def note_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "note", ctx.ramfs, infraction=False, automod=ctx.automod)
    except InfractionGenerationError:
        return 1

    if ctx.verbose and user:
        await message.channel.send(f"Put a note on {user.mention} with ID {user.id}: {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1

    return 0


async def kick_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    modifiers = parse_infraction_modifiers(message.guild, args)

    try:
        member, _, reason, _, dm_sent = await process_infraction(message, args, client, "kick", ramfs, automod=automod, modifiers=modifiers)
    except InfractionGenerationError:
        return 1

    # Attempt to kick user
    if member:
        try:
            if dm_sent:
                await dm_sent  # Wait for dm to be sent before kicking
            await message.guild.kick((member), reason=reason[:512])
        except discord.errors.Forbidden:
            await message.channel.send(f"{BOT_NAME} does not have permission to kick this user.")
            return 1
    else:
        await message.channel.send("User is not in this guild")
        return 1

    if verbose: await message.channel.send(f"Kicked {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


async def ban_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    modifiers = parse_infraction_modifiers(message.guild, args)

    if len(args) >= 3 and args[1] in ["-d", "--days"]:
        try:
            delete_days = int(args[2])
            del args[2]
            del args[1]
        except ValueError:
            delete_days = 0
    else:
        delete_days = 0

    # bounds check (docs say 0 is min and 7 is max)
    if delete_days > 7: delete_days = 7
    elif delete_days < 0: delete_days = 0

    try:
        member, user, reason, _, dm_sent = await process_infraction(message, args, client, "ban", ctx.ramfs, automod=ctx.automod, modifiers=modifiers)
    except InfractionGenerationError:
        return 1

    try:
        if member and dm_sent:
            await dm_sent  # Wait for dm to be sent before banning
        await message.guild.ban(user, delete_message_days=delete_days, reason=reason[:512])
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to ban this user.")
        return 1

    delete_str = f", and deleted {delete_days} day{'s'*(delete_days!=1)} of messages," * bool(delete_days)

    if ctx.verbose: await message.channel.send(f"Banned {user.mention} with ID {user.id}{delete_str} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


async def unban_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "unban", ramfs, infraction=False, automod=automod)
    except InfractionGenerationError:
        return 1

    # Attempt to unban user
    try:
        await message.guild.unban(user, reason=reason[:512])
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to unban this user.")
        return 1
    except discord.errors.NotFound:
        await message.channel.send("This user is not banned")
        return 1

    if verbose: await message.channel.send(f"Unbanned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


class NoMuteRole(Exception):
    __slots__ = ()


async def grab_mute_role(message: discord.Message, ramfs: lexdpyk.ram_filesystem) -> discord.Role:
    if not message.guild:
        raise NoMuteRole("No guild table to find mute role")

    with db_hlapi(message.guild.id) as db:
        mute_role = db.grab_config("mute-role")

        if mute_role and (mute_role_obj := message.guild.get_role(int(mute_role))):
            return mute_role_obj

        else:
            await message.channel.send("ERROR: no mute role set")
            raise NoMuteRole("No mute role")


async def sleep_and_unmute(guild: discord.Guild, member: discord.Member, infractionID: str, mute_role: discord.Role, mutetime: int, ramfs: lexdpyk.ram_filesystem) -> None:

    await asyncio.sleep(mutetime)

    # unmute in db
    with db_hlapi(guild.id) as db:
        if db.is_muted(infractionid=infractionID):
            db.unmute_user(infractionid=infractionID)

            try:
                await member.remove_roles(mute_role)
            except discord.errors.HTTPException:
                pass


async def mute_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    modifiers = parse_infraction_modifiers(message.guild, args)

    # Grab mute time
    if len(args) >= 2:
        try:
            mutetime = MustParseDuration(args[1])
            del args[1]
        except lib_goparsers.errors.ParseFailureError:
            mutetime = 0
    else:
        mutetime = 0

    # This ones for you, curl
    if not 0 <= mutetime < 60 * 60 * 256:
        mutetime = 0

    try:
        mute_role = await grab_mute_role(message, ramfs)
        member, _, reason, infractionID, _ = await process_infraction(message, args, client, "mute", ramfs, automod=automod, modifiers=modifiers)
    except (NoMuteRole, InfractionGenerationError):
        return 1

    # Check they are in the guild
    if not member:
        await message.channel.send("User is not in this guild")
        return 1

    # Attempt to mute user
    try:
        await member.add_roles(mute_role)
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to mute this user.")
        return 1

    if verbose and not mutetime:
        await message.channel.send(f"Muted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())

    # if mutetime call db timed mute
    if mutetime:

        if verbose:
            asyncio.create_task(message.channel.send(f"Muted {member.mention} with ID {member.id} for {format_duration(mutetime)} for {reason}", allowed_mentions=discord.AllowedMentions.none()))

        # Stop other mute timers and add to mutedb
        with db_hlapi(message.guild.id) as db:
            db.unmute_user(userid=member.id)
            db.mute_user(member.id, int(datetime_now().timestamp() + mutetime), infractionID)

        # Create in other thread to not block command execution
        asyncio.create_task(sleep_and_unmute(message.guild, member, infractionID, mute_role, mutetime, ramfs))

    else:

        # When muted with no unmute add to db as 0 timestamp to unmute, program should treat 0 as invalid
        with db_hlapi(message.guild.id) as db:
            db.unmute_user(userid=member.id)
            db.mute_user(member.id, 0, infractionID)

    return 0


async def unmute_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    try:
        mute_role = await grab_mute_role(message, ramfs)
        member, _, reason, _, _ = await process_infraction(message, args, client, "unmute", ramfs, infraction=False, automod=automod)
    except (InfractionGenerationError, NoMuteRole):
        return 1

    if not member:
        await message.channel.send("User is not in this guild")
        return 1

    # Attempt to unmute user
    try:
        await member.remove_roles(mute_role)
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to unmute this user.")
        return 1

    # Unmute in DB
    with db_hlapi(message.guild.id) as db:
        db.unmute_user(userid=member.id)

    if verbose: await message.channel.send(f"Unmuted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


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
    infraction_embed.timestamp = datetime_unix(int(timestamp))

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

    infraction_embed.timestamp = datetime_unix(int(timestamp))

    try:
        await message.channel.send(embed=infraction_embed)
        return 0
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def grab_guild_message(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    discord_message, nargs = await parse_channel_message_noexcept(message, args, client)

    if not discord_message.guild:
        await message.channel.send("ERROR: Message not in any guild")
        return 1

    sendraw = False
    for arg in args[nargs:]:
        if arg in ["-r", "--raw"]:
            sendraw = True
            break

    # Generate replies
    message_content = generate_reply_field(discord_message)

    # Message has been grabbed, start generating embed
    message_embed = discord.Embed(title=f"Message in #{discord_message.channel}", description=message_content, color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs))

    message_embed.set_author(name=str(discord_message.author), icon_url=user_avatar_url(discord_message.author))
    message_embed.timestamp = discord_message.created_at

    # Grab files from cache
    fileobjs = grab_files(discord_message.guild.id, discord_message.id, ctx.kernel_ramfs)

    # Grab files async if not in cache
    if not fileobjs:
        awaitobjs = [asyncio.create_task(i.to_file()) for i in discord_message.attachments]
        fileobjs = [await i for i in awaitobjs]

    if sendraw:
        file_content = io.BytesIO(discord_message.content.encode("utf8"))
        fileobjs.append(discord.File(file_content, filename=f"{discord_message.id}.at.{int(datetime_now().timestamp())}.txt"))

    try:
        await message.channel.send(embed=message_embed, files=fileobjs)
    except discord.errors.HTTPException:
        try:
            await message.channel.send("There were files attached but they exceeded the guild filesize limit", embed=message_embed)
        except discord.errors.Forbidden:
            await message.channel.send(constants.sonnet.error_embed)
            return 1

    return 0


class purger:
    __slots__ = "user_id",

    def __init__(self, user_id: int):
        self.user_id = user_id

    def check(self, message: discord.Message) -> bool:
        return bool(message.author.id == self.user_id)


async def purge_cli(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    if args:
        try:
            limit = int(args[0])
        except ValueError:
            await message.channel.send("ERROR: Limit is not valid int")
            return 1
    else:
        await message.channel.send("ERROR: No limit specified")
        return 1

    if limit > 100 or limit <= 0:
        await message.channel.send("ERROR: Cannot purge more than 100 messages or less than 1 message")
        return 1

    ucheck: Optional[Callable[[discord.Message], bool]]

    try:
        if not (user := client.get_user(int(args[1].strip("<@!>")))):
            user = await client.fetch_user(int(args[1].strip("<@!>")))
        ucheck = purger(user.id).check
    except ValueError:
        await message.channel.send("Invalid UserID")
        return 1
    except IndexError:
        ucheck = None
    except (discord.errors.NotFound, discord.errors.HTTPException):
        await message.channel.send("User does not exist")
        return 1

    try:
        await cast(discord.TextChannel, message.channel).purge(limit=limit, check=ucheck)
        return 0
    except discord.errors.Forbidden:
        await message.channel.send("ERROR: Bot lacks perms to purge")
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
        ts = "No Unmute" if v[2] == 0 else format_duration(v[2] - datetime_now().timestamp())
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


category_info = {'name': 'moderation', 'pretty_name': 'Moderation', 'description': 'Moderation commands.'}

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
    'warn': {
        'pretty_name': 'warn [+modifiers] <uid> [reason]',
        'description': 'Warn a user',
        'permission': 'moderator',
        'execute': warn_user
        },
    'note': {
        'pretty_name': 'note <uid> [note]',
        'description': 'Put a note into a users infraction log, does not dm user',
        'permission': 'moderator',
        'execute': note_user
        },
    'kick': {
        'pretty_name': 'kick [+modifiers] <uid> [reason]',
        'description': 'Kick a user',
        'permission': 'moderator',
        'execute': kick_user
        },
    'ban': {
        'pretty_name': 'ban [+modifiers] <uid> [-d DAYS] [reason]',
        'description': 'Ban a user, optionally delete messages with -d',
        'permission': 'moderator',
        'execute': ban_user
        },
    'unban': {
        'pretty_name': 'unban <uid>',
        'description': 'Unban a user, does not dm user',
        'permission': 'moderator',
        'execute': unban_user
        },
    'mute': {
        'pretty_name': 'mute [+modifiers] <uid> [time[h|m|S]] [reason]',
        'description': 'Mute a user, defaults to no unmute (0s)',
        'permission': 'moderator',
        'execute': mute_user
        },
    'unmute': {
        'pretty_name': 'unmute <uid>',
        'description': 'Unmute a user, does not dm user',
        'permission': 'moderator',
        'execute': unmute_user
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
    'get-message': {
        'alias': 'grab-message'
        },
    'grab-message':
        {
            'pretty_name': 'grab-message <message> [-r]',
            'description': 'Grab a message and show its contents, specify -r to get message content as a file',
            'permission': 'moderator',
            'execute': grab_guild_message
            },
    'purge':
        {
            'pretty_name': 'purge <limit> [user]',
            'description': 'Purge messages from a given channel and optionally only from a specified user',
            'rich_description': 'Can only purge up to 100 messages at a time to prevent catastrophic errors',
            'permission': 'moderator',
            'execute': purge_cli
            }
    }

version_info: str = "1.2.12-DEV"
