# Moderation commands
# bredo, 2020

import importlib

import discord, datetime, time, asyncio

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)
import lib_parsers

importlib.reload(lib_parsers)

from lib_loaders import generate_infractionid
from lib_db_obfuscator import db_hlapi
from lib_parsers import grab_files, generate_reply_field, parse_channel_message

from typing import List, Tuple, Any, Awaitable, Optional


# Catches error if the bot cannot message the user
async def catch_dm_error(user: discord.User, contents: str, log_channel: discord.TextChannel) -> None:
    try:
        await user.send(embed=contents)
    except (AttributeError, discord.errors.HTTPException):
        if log_channel:
            await log_channel.send("ERROR: Could not DM user")


# Sends an infraction to database and log channels if user exists
async def log_infraction(message: discord.Message, client: discord.Client, user: discord.User, moderator_id: int, infraction_reason: str, infraction_type: str,
                         to_dm: bool) -> Tuple[Optional[str], Optional[Awaitable]]:

    if not user:
        return None, None

    with db_hlapi(message.guild.id) as db:
        # Collision test
        while db.grab_infraction(generated_id := generate_infractionid()):
            pass
        # Grab log channel
        log_channel = client.get_channel(int(db.grab_config("infraction-log") or 0))
        # Send infraction to database
        db.add_infraction(generated_id, user.id, moderator_id, infraction_type, infraction_reason, round(time.time()))

    if log_channel:

        log_embed = discord.Embed(title="Sonnet", description=f"New infraction for {user}:", color=0x758cff)
        log_embed.set_thumbnail(url=user.avatar_url)
        log_embed.add_field(name="Infraction ID", value=generated_id)
        log_embed.add_field(name="Moderator", value=client.get_user(int(moderator_id)).mention)
        log_embed.add_field(name="User", value=user.mention)
        log_embed.add_field(name="Type", value=infraction_type)
        log_embed.add_field(name="Reason", value=infraction_reason)

        log_embed.set_footer(text=f"uid: {user.id}, unix: {int(time.time())}")

        asyncio.create_task(log_channel.send(embed=log_embed))

    if not to_dm:
        return generated_id, None

    dm_embed = discord.Embed(title="Sonnet", description=f"You received an infraction in {message.guild.name}:", color=0x758cff)
    dm_embed.set_thumbnail(url=user.avatar_url)
    dm_embed.add_field(name="Infraction ID", value=str(generated_id))
    dm_embed.add_field(name="Type", value=infraction_type)
    dm_embed.add_field(name="Reason", value=infraction_reason)

    dm_embed.timestamp = datetime.datetime.utcnow()

    dm_sent = asyncio.create_task(catch_dm_error(user, dm_embed, log_channel))

    return (generated_id, dm_sent)


class InfractionGenerationError(Exception):
    pass


# General processor for infractions
async def process_infraction(message: discord.Message,
                             args: List[str],
                             client: discord.Client,
                             infraction_type: str,
                             infraction: bool = True) -> Tuple[discord.Member, discord.User, str, Optional[str], Optional[Awaitable]]:

    # Check if automod
    automod: bool = False
    try:
        if (type(args[0]) == int):
            args[0] = str(args[0])
            automod = True
    except IndexError:
        pass

    reason: str = " ".join(args[1:])[:1024] if len(args) > 1 else "No Reason Specified"

    moderator_id: int = client.user.id if automod else message.author.id

    # Test if user is valid
    try:
        member = message.guild.get_member(int(args[0].strip("<@!>")))
        if not (user := client.get_user(int(args[0].strip("<@!>")))):
            user = await client.fetch_user(int(args[0].strip("<@!>")))
    except ValueError:
        await message.channel.send("Invalid UserID")
        raise InfractionGenerationError("Invalid User")
    except IndexError:
        await message.channel.send("No user specified")
        raise InfractionGenerationError("No user specified")
    except (discord.errors.NotFound, discord.errors.HTTPException):
        await message.channel.send("User does not exist")
        raise InfractionGenerationError("User does not exist")

    # Test if user is self
    if member and moderator_id == member.id:
        await message.channel.send(f"Cannot {infraction_type} yourself")
        raise InfractionGenerationError(f"Attempted self {infraction_type}")

    # Do a permission sweep
    if not automod and member and message.guild.roles.index(message.author.roles[-1]) <= message.guild.roles.index(member.roles[-1]):
        await message.channel.send(f"Cannot {infraction_type} a user with the same or higher role as yourself")
        raise InfractionGenerationError(f"Attempted nonperm {infraction_type}")

    # Log infraction
    infraction_id, dm_sent = await log_infraction(message, client, user, moderator_id, reason, infraction_type, infraction)

    return (member, user, reason, infraction_id, dm_sent)


async def warn_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "warn")
    except InfractionGenerationError:
        return 1

    if kwargs["verbose"] and user:
        await message.channel.send(f"Warned {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1


async def note_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        _, user, reason, _, _ = await process_infraction(message, args, client, "note", infraction=False)
    except InfractionGenerationError:
        return 1

    if kwargs["verbose"] and user:
        await message.channel.send(f"Put a note on {user.mention} with ID {user.id}: {reason}", allowed_mentions=discord.AllowedMentions.none())
    elif not user:
        await message.channel.send("User does not exist")
        return 1


async def kick_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        member, _, reason, _, dm_sent = await process_infraction(message, args, client, "kick")
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
        member, user, reason, _, dm_sent = await process_infraction(message, args, client, "ban")
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
        _, user, reason, _, _ = await process_infraction(message, args, client, "unban", infraction=False)
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


async def grab_mute_role(message: discord.Message):

    with db_hlapi(message.guild.id) as db:
        if (mute_role := db.grab_config("mute-role")):
            if (mute_role := message.guild.get_role(int(mute_role))):
                return mute_role
            else:
                await message.channel.send("ERROR: no muterole set")
                raise NoMuteRole("No mute role")
        else:
            await message.channel.send("ERROR: no muterole set")
            raise NoMuteRole("No mute role")


async def sleep_and_unmute(guild: discord.Guild, member: discord.Member, infractionID: str, mute_role: discord.Role, mutetime: int) -> None:

    await asyncio.sleep(mutetime)

    # unmute in db
    with db_hlapi(guild.id) as db:
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
        mute_role = await grab_mute_role(message)
        member, _, reason, infractionID, _ = await process_infraction(message, args, client, "mute")
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

        if not infractionID:
            await message.channel.send("CAUGHT ERROR: There has been an error in grabbing the infractionID\n(User muted but no mute timer created)")
            raise RuntimeError("Impossible code loop detected")

        if kwargs["verbose"]:
            asyncio.create_task(message.channel.send(f"Muted {member.mention} with ID {member.id} for {mutetime}s for {reason}", allowed_mentions=discord.AllowedMentions.none()))

        # Stop other mute timers and add to mutedb
        with db_hlapi(message.guild.id) as db:
            db.unmute_user(userid=member.id)
            db.mute_user(member.id, int(time.time() + mutetime), infractionID)

        # Create in other thread to not block command execution
        asyncio.create_task(sleep_and_unmute(message.guild, member, infractionID, mute_role, mutetime))


async def unmute_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        mute_role = await grab_mute_role(message)
        member, _, reason, _, _ = await process_infraction(message, args, client, "unmute", infraction=False)
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
    with db_hlapi(message.guild.id) as db:
        db.unmute_user(userid=member.id)

    if kwargs["verbose"]: await message.channel.send(f"Unmuted {member.mention} with ID {member.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


async def general_infraction_grabber(message: discord.Message, args: List[str], client: discord.Client):

    # Reparse args
    args = (" ".join(args)).replace("=", " ").split()

    # Parse flags
    selected_chunk = 0
    responsible_mod = None
    infraction_type = None
    user_affected = None
    automod = True
    for index, item in enumerate(args):
        try:
            if item in ["-p", "--page"]:
                selected_chunk = int(float(args[index + 1])) - 1
            elif item in ["-m", "--mod"]:
                responsible_mod = (args[index + 1].strip("<@!>"))
            elif item in ["-u", "--user"]:
                user_affected = (args[index + 1].strip("<@!>"))
            elif item in ["-t", "--type"]:
                infraction_type = (args[index + 1])
            elif item == "--no-automod":
                automod = False
        except (ValueError, IndexError):
            await message.channel.send("Invalid flags supplied")
            return 1

    with db_hlapi(message.guild.id) as db:
        if user_affected:
            infractions = db.grab_user_infractions(user_affected)
            sortmeth = "user"
        elif responsible_mod:
            infractions = db.grab_moderator_infractions(responsible_mod)
            sortmeth = "mod"
        else:
            await message.channel.send("Please specify a user or moderator")
            return 1

    # Generate sorts
    if not automod:
        automod_id = str(client.user.id)
        infractions = filter(lambda i: not (i[2] == automod_id or "[AUTOMOD]" in i[4]), infractions)
    if responsible_mod and sortmeth != "mod":
        infractions = filter(lambda i: i[2] == responsible_mod, infractions)
    if user_affected and sortmeth != "user":
        infractions = filter(lambda i: i[1] == user_affected, infractions)
    if infraction_type:
        infractions = filter(lambda i: i[3] == infraction_type, infractions)

    # Sort newest first
    infractions = sorted(infractions, reverse=True, key=lambda a: a[5])

    # Return if no infractions, this is not an error as it returned a valid status
    if not infractions:
        await message.channel.send("No infractions found")
        return 0

    # Generate chunks from infractions
    do_not_exceed = 1900  # Discord message length limits
    chunks = [""]
    curchunk = 0
    for i in infractions:
        infraction_data = f"{', '.join([i[0], i[3], i[4]])}\n"
        # Make a new page if it overflows
        if (len(chunks[curchunk]) + len(infraction_data)) > do_not_exceed:
            curchunk += 1
            chunks.append("")
        # Add to the current chunk
        chunks[curchunk] = chunks[curchunk] + infraction_data

    # Test if valid page
    if selected_chunk == -1:  # ik it says page 0 but it does -1 on it up above so the user would have entered 0
        await message.channel.send("ERROR: Cannot go to page 0")
        return 1
    elif selected_chunk < -1:
        selected_chunk += 1

    try:
        outdata = chunks[selected_chunk]
    except IndexError:
        await message.channel.send(f"ERROR: No such page {selected_chunk}")
        return 1

    await message.channel.send(f"Page {selected_chunk%len(chunks)+1} / {len(chunks)} ({len(infractions)} infractions)\n```css\nID, Type, Reason\n{outdata}```")


async def search_infractions_by_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    return await general_infraction_grabber(message, args, client)


async def get_detailed_infraction(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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
    infraction_id, user_id, moderator_id, infraction_type, reason, timestamp = infraction

    infraction_embed = discord.Embed(title="Infraction Search", description=f"Infraction for <@{user_id}>:", color=0x758cff)
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)
    infraction_embed.timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))

    await message.channel.send(embed=infraction_embed)


async def delete_infraction(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if args:
        with db_hlapi(message.guild.id) as db:
            infraction = db.grab_infraction(args[0])
            if not infraction:
                await message.channel.send("ERROR: Infraction ID does not exist")
                return 1
            db.delete_infraction(infraction[0])
    else:
        await message.channel.send("ERROR: No argument supplied")
        return 1

    if not kwargs["verbose"]:
        return

    infraction_id, user_id, moderator_id, infraction_type, reason, timestamp = infraction

    infraction_embed = discord.Embed(title="Infraction Deleted", description=f"Infraction for <@{user_id}>:", color=0xd62d20)
    infraction_embed.add_field(name="Infraction ID", value=infraction_id)
    infraction_embed.add_field(name="Moderator", value=f"<@{moderator_id}>")
    infraction_embed.add_field(name="Type", value=infraction_type)
    infraction_embed.add_field(name="Reason", value=reason)
    infraction_embed.timestamp = datetime.datetime.utcfromtimestamp(int(timestamp))

    await message.channel.send(embed=infraction_embed)


async def grab_guild_message(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        discord_message, _ = await parse_channel_message(message, args, client)
    except lib_parsers.errors.message_parse_failure:
        return 1

    # Generate replies
    message_content = generate_reply_field(discord_message)

    # Message has been grabbed, start generating embed
    message_embed = discord.Embed(title=f"Message in #{discord_message.channel}", description=message_content, color=0x758cff)

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
        await message.channel.send("There were files attached but they exceeded the guild filesize limit", embed=message_embed)


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

    try:
        if not (user := client.get_user(int(args[1].strip("<@!>")))):
            user = await client.fetch_user(int(args[1].strip("<@!>")))
        ucheck: Any = purger(user.id).check
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
            'pretty_name': 'search-infractions <-u USER | -m MOD> [-t TYPE] [-p PAGE] [--no-automod]',
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

version_info: str = "1.2.3"
