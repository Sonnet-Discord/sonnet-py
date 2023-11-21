# Moderation commands
# bredo, 2020

from datetime import timedelta
import discord, asyncio, json
from dataclasses import dataclass

import lib_sonnetcommands

from lib_goparsers import ParseDurationSuper
from lib_loaders import generate_infractionid, load_embed_color, load_message_config, embed_colors, datetime_now
from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_user_member_noexcept, format_duration, parse_core_permissions, parse_boolean_strict
from lib_compatibility import user_avatar_url, to_snowflake, GuildMessageable
from lib_sonnetconfig import BOT_NAME
from lib_sonnetcommands import CommandCtx
import lib_constants as constants

from typing import List, Tuple, Awaitable, Optional, Callable, Union, Final, Dict, cast, NamedTuple
import lib_lexdpyk_h as lexdpyk


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

        iterations: int = 0
        iter_limit: Final[int] = 10_000
        # Infraction id collision test
        while db.grab_infraction(generated_id := generate_infractionid()):
            iterations += 1
            if iterations > iter_limit:
                raise lib_sonnetcommands.CommandError(
                    "ERROR: Failed to generate a unique infraction ID after {iter_limit} attempts\n(Do you have too many infractions/too small of a wordlist installed?)"
                    )

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


class InfractionInfo(NamedTuple):
    member: Optional[discord.Member]
    user: InterfacedUser
    reason: str
    infraction_id: str
    dm_await: Optional[Awaitable[None]]
    user_warning: Optional[str]


# General processor for infractions
async def process_infraction_noexcept(
    message: discord.Message,
    args: List[str],
    client: discord.Client,
    i_type: str,
    ramfs: lexdpyk.ram_filesystem,
    infraction: bool = True,
    automod: bool = False,
    modifiers: Optional[List[InfractionModifier]] = None,
    require_in_guild: bool = False
    ) -> InfractionInfo:
    """
    Does infraction processing, raises CommandError on failure
    """
    if not message.guild or not isinstance(message.author, discord.Member):
        raise lib_sonnetcommands.CommandError("User is not member, or no guild")

    reason: str = " ".join(args[1:])[:1024] if len(args) > 1 else "No Reason Specified"

    # Potential BUG: discord.abc.User != discord.user.User under mypy
    # Due to this we have to cast
    moderator = cast(discord.User, client.user if automod else message.author)

    # Test if user is valid
    user, member = await parse_user_member_noexcept(message, args, client)

    if require_in_guild and member is None:
        raise lib_sonnetcommands.CommandError(f"User is not in guild (required to {i_type} user)", private_message=f"{user.mention} is not in this guild")

    local_conf_cache = load_message_config(message.guild.id, ramfs)

    # Test if user is a moderator
    warn_moderator: Optional[str] = None
    if not automod and member and parse_core_permissions(cast(discord.TextChannel, message.channel), member, local_conf_cache, "moderator") and infraction:

        get_help = f"`{local_conf_cache['prefix']}help set-moderator-protect`"

        warn_moderator = f"Note: The user selected is a moderator+ (did you mean to {i_type} this user anyways?)\n(to disallow infractions on a moderator+ see {get_help})"

        if bool(int(local_conf_cache["moderator-protect"])):
            raise lib_sonnetcommands.CommandError(f"Cannot {i_type} specified user, user is a moderator+\n"
                                                  f"(to disable this behavior see {get_help})")

    # Test if user is self
    if member and moderator.id == member.id:
        raise lib_sonnetcommands.CommandError(f"Cannot {i_type} yourself")

    # Do a permission sweep
    if not automod and member and message.guild.roles.index(message.author.roles[-1]) <= message.guild.roles.index(member.roles[-1]):
        raise lib_sonnetcommands.CommandError(f"Cannot {i_type} a user with the same or higher role as yourself", private_message=f"{member.mention} has the same role as you or a higher one")

    modifiers = [] if modifiers is None else modifiers

    # bound modifiers to max of 3 (prevents embed size overflow)
    modlimit: Final = 3
    if len(modifiers) > modlimit:
        raise lib_sonnetcommands.CommandError(f"Too many infraction modifiers passed (limit {modlimit}, given {len(modifiers)})")

    # Log infraction
    infraction_id, dm_sent = await log_infraction(message, client, user, moderator, reason, i_type, infraction, ramfs, modifiers)

    return InfractionInfo(member, user, reason, infraction_id, dm_sent, warn_moderator)


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
                    raise lib_sonnetcommands.CommandError("ERROR: No infraction modifier with name specified", private_message=f"A modifier called `{i}` does not exist")

        return mlist

    return []


async def warn_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    modifiers = parse_infraction_modifiers(message.guild, args)

    _, user, reason, _, _, warn_text = await process_infraction_noexcept(message, args, client, "warn", ctx.ramfs, automod=ctx.automod, modifiers=modifiers)

    if ctx.verbose:
        mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""
        await message.channel.send(f"Warned {user.mention} with ID {user.id}{mod_str} for {reason}", allowed_mentions=discord.AllowedMentions.none())

        if warn_text is not None:
            await message.channel.send(warn_text)

    return 0


async def note_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:

    _, user, reason, _, _, _ = await process_infraction_noexcept(message, args, client, "note", ctx.ramfs, infraction=False, automod=ctx.automod)

    if ctx.verbose:
        await message.channel.send(f"Put a note on {user.mention} with ID {user.id}: {reason}", allowed_mentions=discord.AllowedMentions.none())

    return 0


async def kick_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    modifiers = parse_infraction_modifiers(message.guild, args)

    member, _, reason, _, dm_sent, warn_text = await process_infraction_noexcept(message, args, client, "kick", ramfs, automod=automod, modifiers=modifiers, require_in_guild=True)

    # Attempt to kick user
    if member:
        try:
            if dm_sent:
                await dm_sent  # Wait for dm to be sent before kicking
            await message.guild.kick(to_snowflake(member), reason=reason[:512])

        except discord.errors.Forbidden:
            await message.channel.send(f"{BOT_NAME} does not have permission to kick this user.")
            return 1
    else:
        await message.channel.send("User is not in this guild")
        return 1

    mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""

    if verbose:
        await message.channel.send(f"Kicked {member.mention} with ID {member.id}{mod_str} for {reason}", allowed_mentions=discord.AllowedMentions.none())

        if warn_text is not None:
            await message.channel.send(warn_text)

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

    member, user, reason, _, dm_sent, warn_text = await process_infraction_noexcept(message, args, client, "ban", ctx.ramfs, automod=ctx.automod, modifiers=modifiers)

    try:
        if member and dm_sent:
            await dm_sent  # Wait for dm to be sent before banning
        await message.guild.ban(to_snowflake(user), delete_message_days=delete_days, reason=reason[:512])
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(f"{BOT_NAME} does not have permission to ban this user.")

    unmute_user: bool

    with db_hlapi(message.guild.id) as db:
        if parse_boolean_strict(db.grab_config("unmute-on-ban") or "0") and db.is_muted(userid=user.id):
            unmute_user = True
            db.unmute_user(userid=user.id)
        else:
            unmute_user = False

    unmuted_str = f"{',' * (not delete_days)} and unmuted them," if unmute_user else ""
    delete_str = f",{' and' * (not unmute_user)} deleted {delete_days} day{'s'*(delete_days!=1)} of messages," if delete_days else ""
    mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""

    if ctx.verbose:
        await message.channel.send(f"Banned {user.mention} with ID {user.id}{mod_str}{delete_str}{unmuted_str} for {reason}", allowed_mentions=discord.AllowedMentions.none())

        if warn_text is not None:
            await message.channel.send(warn_text)

    return 0


async def unban_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    _, user, reason, _, _, _ = await process_infraction_noexcept(message, args, client, "unban", ramfs, infraction=False, automod=automod)

    # Attempt to unban user
    try:
        await message.guild.unban(to_snowflake(user), reason=reason[:512])
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to unban this user.")
        return 1
    except discord.errors.NotFound:
        await message.channel.send("This user is not banned.")
        return 1

    if verbose: await message.channel.send(f"Unbanned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


# bans and unbans a user, idk
async def softban_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
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

    member, user, reason, _, dm_sent, warn_text = await process_infraction_noexcept(message, args, client, "softban", ctx.ramfs, automod=ctx.automod, modifiers=modifiers)

    try:
        if member and dm_sent:
            await dm_sent  # Wait for dm to be sent before banning
        await message.guild.ban(to_snowflake(user), delete_message_days=delete_days, reason=reason[:512])

    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(f"{BOT_NAME} does not have permission to ban this user.")

    try:
        await message.guild.unban(to_snowflake(user), reason=reason[:513])
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(f"{BOT_NAME} does not have permission to unban this user.")
    except discord.errors.NotFound:
        raise lib_sonnetcommands.CommandError(f"Unbanning failed: User is not banned.\n(Maybe user was unbanned before {BOT_NAME} could?)\n(Maybe discord did not register the ban properly?)")

    delete_str = f", and deleted {delete_days} day{'s'*(delete_days!=1)} of messages," if delete_days else ""
    mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""

    if ctx.verbose:
        await message.channel.send(f"Softbanned {user.mention} with ID {user.id}{mod_str}{delete_str} for {reason}", allowed_mentions=discord.AllowedMentions.none())

        if warn_text is not None:
            await message.channel.send(warn_text)

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
                await member.remove_roles(to_snowflake(mute_role))
            except discord.errors.HTTPException:
                pass


def parse_duration_for_mutes(args: List[str], inf_name: str, /) -> Tuple[int, Optional[str]]:
    """
    Parses a duration from args to get mutetime/timeouttime and returns string if a duration was not passed in the correct place but is valid
    abstracts logic for mutes/timeouts
    """

    # Grab mute time
    if len(args) >= 2:
        mutetime = ParseDurationSuper(args[1])
        if mutetime is not None:
            del args[1]
    else:
        mutetime = None

    misplaced_duration: Optional[str] = None
    if mutetime is None:
        for i in args[1:]:
            if ParseDurationSuper(i) is not None:
                misplaced_duration = i
                break

    if mutetime is None:
        mutetime = 0

    duration_str: Optional[str]

    if misplaced_duration is not None:
        duration_str = f"\n(No {inf_name} length was specified, but one of the reason items `{misplaced_duration}` is a valid duration, did you mean to {inf_name} for this length?)"
    else:
        duration_str = None

    return mutetime, duration_str


async def mute_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    ramfs = ctx.ramfs
    automod = ctx.automod
    verbose = ctx.verbose

    mutetime, duration_str = parse_duration_for_mutes(args, "mute")

    modifiers = parse_infraction_modifiers(message.guild, args)

    # This ones for you, curl
    # Replaced with 28 day limit from 256 hours to match new timeout api
    if not 0 <= mutetime < (60 * 60 * 24) * 28:
        mutetime = 0

    with db_hlapi(message.guild.id) as db:
        if bool(int(db.grab_config("show-mutetime") or "0")):
            ts = "Infinite" if mutetime == 0 else format_duration(mutetime)
            length = f"mutelength({ts})"
            modifiers.append(InfractionModifier(length, "Length", ts))

    try:
        mute_role = await grab_mute_role(message, ramfs)
    except NoMuteRole:
        return 1

    member, _, reason, infractionID, _, warn_text = await process_infraction_noexcept(message, args, client, "mute", ramfs, automod=automod, modifiers=modifiers, require_in_guild=True)

    # Check they are in the guild
    if not member:
        await message.channel.send("User is not in this guild")
        return 1

    # Attempt to mute user
    try:
        await member.add_roles(to_snowflake(mute_role))
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to mute this user.")
        return 1

    mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""

    if verbose and not mutetime:
        await message.channel.send(f"Muted {member.mention} with ID {member.id}{mod_str} for {reason}{duration_str or ''}", allowed_mentions=discord.AllowedMentions.none())

        if warn_text is not None:
            await message.channel.send(warn_text)

    # if mutetime call db timed mute
    if mutetime:

        if verbose:
            asyncio.create_task(
                message.channel.send(f"Muted {member.mention} with ID {member.id}{mod_str} for {format_duration(mutetime)} for {reason}", allowed_mentions=discord.AllowedMentions.none())
                )

            if warn_text is not None:
                asyncio.create_task(message.channel.send(warn_text))

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
    except NoMuteRole:
        return 1

    member, _, reason, _, _, _ = await process_infraction_noexcept(message, args, client, "unmute", ramfs, infraction=False, automod=automod, require_in_guild=True)

    if not member:
        await message.channel.send("User is not in this guild")
        return 1

    # Attempt to unmute user
    try:
        await member.remove_roles(to_snowflake(mute_role))
    except discord.errors.Forbidden:
        await message.channel.send(f"{BOT_NAME} does not have permission to unmute this user.")
        return 1

    # Unmute in DB
    with db_hlapi(message.guild.id) as db:
        db.unmute_user(userid=member.id)

    if verbose: await message.channel.send(f"Unmuted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


async def timeout_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    mutetime, duration_str = parse_duration_for_mutes(args, "timeout")

    if mutetime >= ((60 * 60) * 24) * 28 or mutetime <= 0:
        mutetime = ((60 * 60) * 24) * 28

    modifiers = parse_infraction_modifiers(message.guild, args)

    member, _, reason, _, _, warn_text = await process_infraction_noexcept(message, args, client, "timeout", ctx.ramfs, automod=ctx.automod, modifiers=modifiers, require_in_guild=True)

    if not member:
        raise lib_sonnetcommands.CommandError("ERROR: User not in guild")

    try:
        await member.timeout(timedelta(seconds=mutetime), reason=reason[:512])
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(f"{BOT_NAME} does not have permission to timeout this user.")

    mod_str = f" with {','.join(m.title for m in modifiers)}" if modifiers else ""

    if ctx.verbose:
        await message.channel.send(
            f"Timed out {member.mention} with ID {member.id}{mod_str} for {format_duration(mutetime)} for {reason}{duration_str or ''}", allowed_mentions=discord.AllowedMentions.none()
            )

        if warn_text is not None:
            await message.channel.send(warn_text)

    return 0


async def un_timeout_user(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    member, _, reason, _, _, _ = await process_infraction_noexcept(message, args, client, "untimeout", ctx.ramfs, infraction=False, automod=ctx.automod, require_in_guild=True)

    if not member:
        raise lib_sonnetcommands.CommandError("ERROR: User is not a member")

    # Attempt to untimeout user
    try:
        await member.timeout(None, reason=reason[:512])
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(f"{BOT_NAME} does not have permission to untimeout this user.")

    if ctx.verbose:
        await message.channel.send(f"Removed timeout for {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    return 0


class purger:
    __slots__ = "user_id", "message_id"

    def __init__(self, user_id: Optional[int], message: discord.Message):
        self.user_id = user_id
        self.message_id = message.id

    def check(self, message: discord.Message) -> bool:
        if message.id == self.message_id:
            return False

        if self.user_id is None:
            return True

        return bool(message.author.id == self.user_id)


async def purge_cli(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:

    if args:
        try:
            limit = int(args[0])
        except ValueError:
            raise lib_sonnetcommands.CommandError("ERROR: Limit is not valid int", private_message=f"`{args[0]}` is not a valid int")
    else:
        raise lib_sonnetcommands.CommandError("ERROR: No limit specified")

    if limit > 100 or limit <= 0:
        raise lib_sonnetcommands.CommandError("ERROR: Cannot purge more than 100 messages or less than 1 message")

    ucheck: Callable[[discord.Message], bool]

    try:
        if not (user := client.get_user(int(args[1].strip("<@!>")))):
            user = await client.fetch_user(int(args[1].strip("<@!>")))
        ucheck = purger(user.id, message).check
    except ValueError:
        raise lib_sonnetcommands.CommandError("Invalid UserID", private_message=f"`{args[1]}` is not a valid user id")
    except IndexError:
        ucheck = purger(None, message).check
    except (discord.errors.NotFound, discord.errors.HTTPException):
        raise lib_sonnetcommands.CommandError("User does not exist")

    try:
        purged = await cast(GuildMessageable, message.channel).purge(limit=limit, check=ucheck)
        await message.channel.send(f"Purged {len(purged)} message{'s' * (len(purged)!=1)}, initiated by {message.author.mention}", allowed_mentions=discord.AllowedMentions.none())
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError("ERROR: Bot lacks perms to purge")


category_info = {'name': 'moderation', 'pretty_name': 'Moderation', 'description': 'Moderation commands.'}

commands = {
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
        'pretty_name': 'unban <uid> [reason]',
        'description': 'Unban a user, does not dm user',
        'permission': 'moderator',
        'execute': unban_user
        },
    'softban':
        {
            'pretty_name': 'softban [+modifiers] <uid> [-d DAYS] [reason]',
            'description': 'Softban (ban and then immediately unban) a user, optionally delete messages with -d',
            'permission': 'moderator',
            'execute': softban_user,
            },
    'mute': {
        'pretty_name': 'mute [+modifiers] <uid> [time[h|m|S]] [reason]',
        'description': 'Mute a user, defaults to no unmute (0s)',
        'permission': 'moderator',
        'execute': mute_user
        },
    'unmute': {
        'pretty_name': 'unmute <uid> [reason]',
        'description': 'Unmute a user, does not dm user',
        'permission': 'moderator',
        'execute': unmute_user
        },
    "timeout":
        {
            'pretty_name': 'timeout [+modifiers] <uid> [time[h|m|S]] [reason]',
            'description': 'Timeout a member, defaults to longest timeout possible (28 days)',
            'permission': "moderator",
            "execute": timeout_user,
            },
    "untimeout": {
        'alias': "remove-timeout",
        },
    "remove-timeout": {
        'pretty_name': 'remove-timeout <uid> [reason]',
        'description': 'Remove a timeout on a member',
        'permission': "moderator",
        "execute": un_timeout_user,
        },
    'purge':
        {
            'pretty_name': 'purge <limit> [user]',
            'description': 'Purge messages from a given channel and optionally only from a specified user, this will not purge the command invocation',
            'rich_description':
                ('Can only purge up to 100 messages at a time to prevent catastrophic errors, '
                 'will print a success message indicating how many messages were purged and who invoked the command'),
            'permission': 'moderator',
            'execute': purge_cli
            }
    }

version_info: str = "2.0.2"
