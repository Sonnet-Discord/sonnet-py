# Moderation commands
# bredo, 2020

import importlib

import discord, time, asyncio, math
from datetime import datetime

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)
import lib_parsers

importlib.reload(lib_parsers)
import lib_constants

importlib.reload(lib_constants)

from lib_loaders import generate_infractionid, load_embed_color, embed_colors, get_guild_lock
from lib_db_obfuscator import db_hlapi
from lib_parsers import grab_files, generate_reply_field, parse_channel_message, parse_user_member
import lib_constants as constants

from typing import List, Tuple, Any, Awaitable, Optional, Callable, cast
import lib_lexdpyk_h as lexdpyk


# Catches error if the bot cannot message the user
async def catch_dm_error(user: discord.User, contents: str, log_channel: discord.TextChannel) -> None:
    try:
        await user.send(embed=contents)
    except (AttributeError, discord.errors.HTTPException):
        if log_channel:
            try:
                await log_channel.send(f"ERROR: {user.mention}:{user.id} Could not DM user", allowed_mentions=discord.AllowedMentions.none())
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


# Sends an infraction to database and log channels if user exists
async def log_infraction(
    message: discord.Message, client: discord.Client, user: discord.User, moderator: discord.User, infraction_reason: str, infraction_type: str, to_dm: bool, ramfs: lexdpyk.ram_filesystem
    ) -> Tuple[str, Optional[Awaitable[None]]]:

    timestamp = datetime.utcnow()  # Infraction timestamp

    # Define db outputs scoped correctly
    generated_id: str
    log_channel: Optional[discord.TextChannel]

    with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, ramfs)) as db:

        # Infraction id collision test
        while db.grab_infraction(generated_id := generate_infractionid()):
            continue

        # Grab log channel
        try:
            chan: int = int(db.grab_config("infraction-log") or "0")
        except ValueError:
            chan = 0
        log_channel = client.get_channel(chan)

        # Send infraction to database
        db.add_infraction(generated_id, user.id, moderator.id, infraction_type, infraction_reason, int(timestamp.timestamp()))

    if log_channel:

        log_embed = discord.Embed(title="Sonnet", description=f"New infraction for {user}:", color=load_embed_color(message.guild, embed_colors.creation, ramfs))
        log_embed.set_thumbnail(url=user.avatar_url)
        log_embed.add_field(name="Infraction ID", value=generated_id)
        log_embed.add_field(name="Moderator", value=moderator.mention)
        log_embed.add_field(name="User", value=user.mention)
        log_embed.add_field(name="Type", value=infraction_type)
        log_embed.add_field(name="Reason", value=infraction_reason)

        log_embed.set_footer(text=f"uid: {user.id}, unix: {int(timestamp.timestamp())}")

        asyncio.create_task(catch_logging_error(log_embed, log_channel))

    if not to_dm:
        return generated_id, None

    dm_embed = discord.Embed(title="Sonnet", description=f"You received an infraction in {message.guild.name}:", color=load_embed_color(message.guild, embed_colors.primary, ramfs))
    dm_embed.set_thumbnail(url=user.avatar_url)
    dm_embed.add_field(name="Infraction ID", value=str(generated_id))
    dm_embed.add_field(name="Type", value=infraction_type)
    dm_embed.add_field(name="Reason", value=infraction_reason)

    dm_embed.timestamp = timestamp

    dm_sent = asyncio.create_task(catch_dm_error(user, dm_embed, log_channel))

    return (generated_id, dm_sent)


class InfractionGenerationError(Exception):
    pass


# General processor for infractions
async def process_infraction(message: discord.Message,
                             args: List[str],
                             client: discord.Client,
                             infraction_type: str,
                             ramfs: lexdpyk.ram_filesystem,
                             infraction: bool = True) -> Tuple[discord.Member, discord.User, str, str, Optional[Awaitable[None]]]:

    # Check if automod
    automod: bool = False
    try:
        if isinstance(args[0], int):
            args[0] = str(args[0])
            automod = True
    except IndexError:
        pass

    reason: str = " ".join(args[1:])[:1024] if len(args) > 1 else "No Reason Specified"

    moderator: discord.User = client.user if automod else message.author

    # Test if user is valid
    try:
        user, member = await parse_user_member(message, args, client)
    except lib_parsers.errors.user_parse_error:
        raise InfractionGenerationError("Could not parse user")

    # Test if user is self
    if member and moderator.id == member.id:
        await message.channel.send(f"Cannot {infraction_type} yourself")
        raise InfractionGenerationError(f"Attempted self {infraction_type}")

    # Do a permission sweep
    if not automod and member and message.guild.roles.index(message.author.roles[-1]) <= message.guild.roles.index(member.roles[-1]):
        await message.channel.send(f"Cannot {infraction_type} a user with the same or higher role as yourself")
        raise InfractionGenerationError(f"Attempted nonperm {infraction_type}")

    # Log infraction
    infraction_id, dm_sent = await log_infraction(message, client, user, moderator, reason, infraction_type, infraction, ramfs)

    return (member, user, reason, infraction_id, dm_sent)


async def warn_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "warn", kwargs["ramfs"])
    except InfractionGenerationError:
        return 1

    if kwargs["verbose"] and user:
        await message.channel.send(f"Warned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1


async def note_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "note", kwargs["ramfs"], infraction=False)
    except InfractionGenerationError:
        return 1

    if kwargs["verbose"] and user:
        await message.channel.send(f"Put a note on {user.mention} with ID {user.id}: {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1


async def kick_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        member, _, reason, _, dm_sent = await process_infraction(message, args, client, "kick", kwargs["ramfs"])
    except InfractionGenerationError:
        return 1

    # Attempt to kick user
    if member:
        try:
            if dm_sent:
                await dm_sent  # Wait for dm to be sent before kicking
            await message.guild.kick((member), reason=reason)
        except discord.errors.Forbidden:
            await message.channel.send("The bot does not have permission to kick this user.")
            return 1
    else:
        await message.channel.send("User is not in this guild")
        return 1

    if kwargs["verbose"]: await message.channel.send(f"Kicked {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


async def ban_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        member, user, reason, _, dm_sent = await process_infraction(message, args, client, "ban", kwargs["ramfs"])
    except InfractionGenerationError:
        return 1

    # Attempt to ban user
    try:
        if member:
            if dm_sent:
                await dm_sent  # Wait for dm to be sent before banning
        await message.guild.ban(user, delete_message_days=0, reason=reason)

    except discord.errors.Forbidden:
        await message.channel.send("The bot does not have permission to ban this user.")
        return 1

    if kwargs["verbose"]: await message.channel.send(f"Banned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


async def unban_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "unban", kwargs["ramfs"], infraction=False)
    except InfractionGenerationError:
        return 1

    # Attempt to unban user
    try:
        await message.guild.unban(user, reason=reason)
    except discord.errors.Forbidden:
        await message.channel.send("The bot does not have permission to unban this user.")
        return 1
    except discord.errors.NotFound:
        await message.channel.send("This user is not banned")
        return 1

    if kwargs["verbose"]: await message.channel.send(f"Unbanned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


class NoMuteRole(Exception):
    pass


async def grab_mute_role(message: discord.Message, ramfs: lexdpyk.ram_filesystem) -> discord.Role:

    with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, ramfs)) as db:
        if (mute_role := db.grab_config("mute-role")):
            if (mute_role := message.guild.get_role(int(mute_role))):
                return mute_role
            else:
                await message.channel.send("ERROR: no muterole set")
                raise NoMuteRole("No mute role")
        else:
            await message.channel.send("ERROR: no muterole set")
            raise NoMuteRole("No mute role")


async def sleep_and_unmute(guild: discord.Guild, member: discord.Member, infractionID: str, mute_role: discord.Role, mutetime: int, ramfs: lexdpyk.ram_filesystem) -> None:

    await asyncio.sleep(mutetime)

    # unmute in db
    with db_hlapi(guild.id, lock=get_guild_lock(guild, ramfs)) as db:
        if db.is_muted(infractionid=infractionID):
            db.unmute_user(infractionid=infractionID)

            try:
                await member.remove_roles(mute_role)
            except discord.errors.HTTPException:
                pass


async def mute_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    # Grab mute time
    if len(args) >= 2:
        try:
            if args[1][-1] in (multi := {"s": 1, "m": 60, "h": 3600}):
                mutetime = int(args[1][:-1]) * multi[args[1][-1]]
                del args[1]
            else:
                mutetime = int(args[1])
                del args[1]
        except (ValueError, TypeError):
            mutetime = 0
    else:
        mutetime = 0

    # This ones for you, curl
    if mutetime >= 60 * 60 * 256 or mutetime < 0:
        mutetime = 0

    try:
        mute_role = await grab_mute_role(message, kwargs["ramfs"])
        member, _, reason, infractionID, _ = await process_infraction(message, args, client, "mute", kwargs["ramfs"])
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
        await message.channel.send("The bot does not have permission to mute this user.")
        return 1

    if kwargs["verbose"] and not mutetime:
        await message.channel.send(f"Muted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())

    if mutetime:

        if kwargs["verbose"]:
            asyncio.create_task(message.channel.send(f"Muted {member.mention} with ID {member.id} for {mutetime}s for {reason}", allowed_mentions=discord.AllowedMentions.none()))

        # Stop other mute timers and add to mutedb
        with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, kwargs["ramfs"])) as db:
            db.unmute_user(userid=member.id)
            db.mute_user(member.id, int(time.time() + mutetime), infractionID)

        # Create in other thread to not block command execution
        asyncio.create_task(sleep_and_unmute(message.guild, member, infractionID, mute_role, mutetime, kwargs["ramfs"]))


async def unmute_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        mute_role = await grab_mute_role(message, kwargs["ramfs"])
        member, _, reason, _, _ = await process_infraction(message, args, client, "unmute", kwargs["ramfs"], infraction=False)
    except (InfractionGenerationError, NoMuteRole):
        return 1

    if not member:
        await message.channel.send("User is not in this guild")
        return 1

    # Attempt to unmute user
    try:
        await member.remove_roles(mute_role)
    except discord.errors.Forbidden:
        await message.channel.send("The bot does not have permission to unmute this user.")
        return 1

    # Unmute in DB
    with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, kwargs["ramfs"])) as db:
        db.unmute_user(userid=member.id)

    if kwargs["verbose"]: await message.channel.send(f"Unmuted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


async def search_infractions_by_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    tstart = time.monotonic()

    ramfs: lexdpyk.ram_filesystem = kwargs["ramfs"]

    # Reparse args
    args = (" ".join(args)).replace("=", " ").split()

    # Parse flags
    selected_chunk: int = 0
    responsible_mod: Optional[int] = None
    infraction_type: Optional[str] = None
    per_page: int = 20
    user_affected: Optional[int] = None
    automod: bool = True
    for index, item in enumerate(args):
        try:
            if item in ["-p", "--page"]:
                selected_chunk = int(float(args[index + 1])) - 1
            elif item in ["-m", "--mod"]:
                responsible_mod = int(args[index + 1].strip("<@!>"))
            elif item in ["-u", "--user"]:
                user_affected = int(args[index + 1].strip("<@!>"))
            elif item in ["-i", "--infractioncount"]:
                per_page = int(args[index + 1])
            elif item in ["-t", "--type"]:
                infraction_type = (args[index + 1])
            elif item == "--no-automod":
                automod = False
        except (ValueError, IndexError):
            await message.channel.send("Invalid flags supplied")
            return 1

    if per_page > 40 or per_page < 5:
        await message.channel.send("ERROR: Cannot exeed range 5-40 infractions per page")
        return 1

    with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, ramfs)) as db:
        if user_affected or responsible_mod:
            infractions = cast(List[Tuple[str, str, str, str, str, int]], db.grab_filter_infractions(user=user_affected, moderator=responsible_mod, itype=infraction_type, automod=automod))
        else:
            await message.channel.send("Please specify a user or moderator")
            return 1

    # Sort newest first
    infractions = sorted(infractions, reverse=True, key=lambda a: a[5])

    # Return if no infractions, this is not an error as it returned a valid status
    if not infractions:
        await message.channel.send("No infractions found")
        return 0

    cpagecount = math.ceil(len(infractions) / per_page)

    # Test if valid page
    if selected_chunk == -1:  # ik it says page 0 but it does -1 on it up above so the user would have entered 0
        await message.channel.send("ERROR: Cannot go to page 0")
        return 1
    elif selected_chunk < -1:
        selected_chunk %= cpagecount
        selected_chunk += 1

    if selected_chunk > cpagecount or selected_chunk < 0:
        await message.channel.send(f"ERROR: No such page {selected_chunk+1}")
        return 1

    chunk = ""
    for i in infractions[selected_chunk * per_page:selected_chunk * per_page + per_page]:
        chunk += f"{', '.join([i[0], i[3], i[4]])[:math.floor(1900/per_page)]}\n"

    tprint = round((time.monotonic() - tstart) * 10000) / 10

    await message.channel.send(f"Page {selected_chunk+1} / {cpagecount} ({len(infractions)} infractions) ({tprint}ms)\n```css\nID, Type, Reason\n{chunk}```")


async def get_detailed_infraction(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if args:
        with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, kwargs["ramfs"])) as db:
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

    infraction_embed = discord.Embed(title="Infraction Search", description=f"Infraction for <@{user_id}>:", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)

    infraction_embed.set_footer(text=f"uid: {user_id}, unix: {timestamp}")
    infraction_embed.timestamp = datetime.utcfromtimestamp(int(timestamp))

    try:
        await message.channel.send(embed=infraction_embed)
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def delete_infraction(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if args:
        with db_hlapi(message.guild.id, lock=get_guild_lock(message.guild, kwargs["ramfs"])) as db:
            infraction = db.grab_infraction(args[0])
            if not infraction:
                await message.channel.send("ERROR: Infraction ID does not exist")
                return 1
            # pylint: disable=E1136
            db.delete_infraction(infraction[0])
    else:
        await message.channel.send("ERROR: No argument supplied")
        return 1

    if not kwargs["verbose"]:
        return

    # pylint: disable=E0633
    infraction_id, user_id, moderator_id, infraction_type, reason, timestamp = infraction

    infraction_embed = discord.Embed(title="Infraction Deleted", description=f"Infraction for <@{user_id}>:", color=load_embed_color(message.guild, embed_colors.deletion, kwargs["ramfs"]))
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)

    infraction_embed.set_footer(text=f"uid: {user_id}, unix: {timestamp}")

    infraction_embed.timestamp = datetime.utcfromtimestamp(int(timestamp))

    try:
        await message.channel.send(embed=infraction_embed)
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def grab_guild_message(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        discord_message, _ = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    # Generate replies
    message_content = generate_reply_field(discord_message)

    # Message has been grabbed, start generating embed
    message_embed = discord.Embed(title=f"Message in #{discord_message.channel}", description=message_content, color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))

    message_embed.set_author(name=discord_message.author, icon_url=discord_message.author.avatar_url)
    message_embed.timestamp = discord_message.created_at

    # Grab files from cache
    fileobjs = grab_files(discord_message.guild.id, discord_message.id, kwargs["kernel_ramfs"])

    # Grab files async if not in cache
    if not fileobjs:
        awaitobjs = [asyncio.create_task(i.to_file()) for i in discord_message.attachments]
        fileobjs = [await i for i in awaitobjs]

    try:
        await message.channel.send(embed=message_embed, files=fileobjs)
    except discord.errors.HTTPException:
        try:
            await message.channel.send("There were files attached but they exceeded the guild filesize limit", embed=message_embed)
        except discord.errors.Forbidden:
            await message.channel.send(constants.sonnet.error_embed)
            return 1


class purger:
    def __init__(self, user_id: int):
        self.user_id = user_id

    def check(self, message: discord.Message) -> bool:
        return bool(message.author.id == self.user_id)


async def purge_cli(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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
        await message.channel.purge(limit=limit, check=ucheck)
    except discord.errors.Forbidden:
        await message.channel.send("ERROR: Bot lacks perms to purge")
        return 1


category_info = {'name': 'moderation', 'pretty_name': 'Moderation', 'description': 'Moderation commands.'}

commands = {
    'warn': {
        'pretty_name': 'warn <uid> [reason]',
        'description': 'Warn a user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': warn_user
        },
    'note': {
        'pretty_name': 'note <uid> [note]',
        'description': 'Put a note into a users infraction log, does not dm user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': note_user
        },
    'kick': {
        'pretty_name': 'kick <uid> [reason]',
        'description': 'Kick a user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': kick_user
        },
    'ban': {
        'pretty_name': 'ban <uid> [reason]',
        'description': 'Ban a user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': ban_user
        },
    'unban': {
        'pretty_name': 'unban <uid>',
        'description': 'Unban a user, does not dm user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': unban_user
        },
    'mute': {
        'pretty_name': 'mute <uid> [time[h|m|S]] [reason]',
        'description': 'Mute a user, defaults to no unmute (0s)',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': mute_user
        },
    'unmute': {
        'pretty_name': 'unmute <uid>',
        'description': 'Unmute a user, does not dm user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': unmute_user
        },
    'warnings': {
        'alias': 'search-infractions'
        },
    'list-infractions': {
        'alias': 'search-infractions'
        },
    'search-infractions':
        {
            'pretty_name': 'search-infractions <-u USER | -m MOD> [-t TYPE] [-p PAGE] [-i INF PER PAGE] [--no-automod]',
            'description': 'Grab infractions of a user',
            'rich_description': 'Supports negative indexing in pager, flags are unix like',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': search_infractions_by_user
            },
    'get-infraction': {
        'alias': 'infraction-details'
        },
    'infraction-details':
        {
            'pretty_name': 'infraction-details <infractionID>',
            'description': 'Grab details of an infractionID',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': get_detailed_infraction
            },
    'remove-infraction': {
        'alias': 'delete-infraction'
        },
    'rm-infraction': {
        'alias': 'delete-infraction'
        },
    'delete-infraction':
        {
            'pretty_name': 'delete-infraction <infractionID>',
            'description': 'Delete an infraction by infractionID',
            'permission': 'administrator',
            'cache': 'keep',
            'execute': delete_infraction
            },
    'get-message': {
        'alias': 'grab-message'
        },
    'grab-message': {
        'pretty_name': 'grab-message <message>',
        'description': 'Grab a message and show its contents',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': grab_guild_message
        },
    'purge':
        {
            'pretty_name': 'purge <limit> [user]',
            'description': 'Purge messages from a given channel and optionally only from a specified user',
            'rich_description': 'Can only purge up to 100 messages at a time to prevent catastrophic errors',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': purge_cli
            }
    }

version_info: str = "1.2.6-DEV"
