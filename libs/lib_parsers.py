# Parsers for message handling
# Ultrabear 2020

from __future__ import annotations

import importlib

import lz4.frame, discord, os, json, hashlib, io, warnings, math

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_encryption_wrapper

importlib.reload(lib_encryption_wrapper)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_constants

importlib.reload(lib_constants)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)

from lib_sonnetconfig import REGEX_VERSION
from lib_db_obfuscator import db_hlapi
from lib_encryption_wrapper import encrypted_reader
import lib_constants as constants

from typing import Callable, Iterable, Optional, Any, Tuple, Dict, Union, List, TypeVar, Literal, overload, cast
import lib_lexdpyk_h as lexdpyk

# Import re here to trick type checker into using re stubs even if importlib grabs re2, they (should) have the same stubs
import re

# Place this in the globals scope by hand to avoid pyflakes saying its a redefinition
globals()["re"] = importlib.import_module(REGEX_VERSION)


class errors:
    class log_channel_update_error(RuntimeError):
        __slots__ = ()

    class message_parse_failure(Exception):
        __slots__ = ()

    class user_parse_error(Exception):
        __slots__ = ()


_urlFilter = re.compile(r"[^a-z0-9\-\.]+")


def _compileurl(urllist: List[str]) -> str:

    urllist = [_urlFilter.sub("", i).replace(".", r"\.") for i in urllist]

    # discord renders a preview even if the https and url span multiple lines so account for newline and dont capture it
    # ex: https://website.domain/page would render a preview, but so would
    #  https://
    #  website.domain
    #  /page
    # and other variants
    return f"(https?://)(?:\n)?({'|'.join(urllist)})"


unicodeFilter = re.compile(r'[^a-z0-9 ]+')

_parse_blacklist_inputs = Tuple[discord.Message, Dict[str, Any], lexdpyk.ram_filesystem]


def _formatregexfind(gex: List[Any]) -> str:
    return ", ".join(i if isinstance(i, str) else "".join(i) for i in gex)


# This exists because type checkers can't infer lambda return types or something
def returnsNone() -> None:
    ...


# Run a blacklist pass over a messages content and files
def parse_blacklist(indata: _parse_blacklist_inputs) -> tuple[bool, bool, list[str]]:
    """
    Deprecated, this should be in dlib_messages.py
    Parse the blacklist over a message object

    :returns: Tuple[bool, bool, List[str]] -- broke blacklist, broke notifier list, list of strings of infraction messages
    """
    message, blacklist, ramfs = indata

    if not message.guild:
        return False, False, []

    # Preset values
    broke_blacklist = False
    notifier = False
    infraction_type = []

    # Compilecheck regex
    try:
        ramfs.ls(f"{message.guild.id}/regex")
    except FileNotFoundError:
        # Compiles regex blacklists if they are not precompiled

        with db_hlapi(message.guild.id) as db:
            reglist = {}
            for regex_type in ["regex-blacklist", "regex-notifier"]:
                if dat := db.grab_config(regex_type):
                    reglist[regex_type] = [" ".join(i.split(" ")[1:])[1:-2] for i in json.loads(dat)["blacklist"]]
                else:
                    reglist[regex_type] = []

        for regex_type in ["regex-blacklist", "regex-notifier"]:
            ramfs.mkdir(f"{message.guild.id}/regex/{regex_type}")
            for i in reglist[regex_type]:
                # name ramfs file using sha256 hex and only take last 32 bytes to avoid directory name exploit
                # (forward slash in regex would build a new directory)
                regexname = hex(int.from_bytes(hashlib.sha256(i.encode("utf8")).digest(), "big"))[-32:]
                ramfs.create_f(f"{message.guild.id}/regex/{regex_type}/{regexname}", f_type=re.compile, f_args=[i])

        if blacklist["url-blacklist"]:
            ramfs.create_f(f"{message.guild.id}/regex/url", f_type=re.compile, f_args=[_compileurl(blacklist["url-blacklist"])])
        else:
            ramfs.create_f(f"{message.guild.id}/regex/url", f_type=returnsNone)

    # Load blacklist from ramfs cache into temp conf_cache
    blacklist["regex-blacklist"] = [ramfs.read_f(f"{message.guild.id}/regex/regex-blacklist/{i}") for i in ramfs.ls(f"{message.guild.id}/regex/regex-blacklist")[0]]
    blacklist["regex-notifier"] = [ramfs.read_f(f"{message.guild.id}/regex/regex-notifier/{i}") for i in ramfs.ls(f"{message.guild.id}/regex/regex-notifier")[0]]
    blacklist["url-blacklist_regex"] = ramfs.read_f(f"{message.guild.id}/regex/url")

    # Check that member is still part of guild (yes this is a race cond that happens)
    if not isinstance(message.author, discord.Member):
        return False, False, []

    # If in whitelist, skip parse to save resources
    if message.author.guild and blacklist["blacklist-whitelist"] and int(blacklist["blacklist-whitelist"]) in [i.id for i in message.author.roles]:
        return (False, False, [])

    text_to_blacklist = unicodeFilter.sub('', message.content.lower().replace(":", " ").replace("\n", " "))
    LowerCaseContent = message.content.lower()

    # Check message against word blacklist
    word_blacklist: List[str] = blacklist["word-blacklist"]
    for i in text_to_blacklist.split(" "):
        if i in word_blacklist:
            broke_blacklist = True
            infraction_type.append(f"Word({i})")

    # Check message against word in word blacklist
    word_in_word_blacklist: List[str] = blacklist["word-in-word-blacklist"]
    for i in word_in_word_blacklist:
        if i in text_to_blacklist.replace(" ", ""):
            broke_blacklist = True
            infraction_type.append(f"WordInWord({i})")

    # Check message against REGEXP blacklist
    regex_blacklist = cast(List["re.Pattern[str]"], blacklist["regex-blacklist"])
    for r in regex_blacklist:
        try:
            if broke := r.findall(LowerCaseContent):
                broke_blacklist = True
                infraction_type.append(f"RegEx({_formatregexfind(broke)})")
        except re.error:
            pass  # GC for old regex

    # Check message against REGEXP notifier list
    regex_notifier = cast(List["re.Pattern[str]"], blacklist["regex-notifier"])
    for r in regex_notifier:
        if r.findall(LowerCaseContent):
            notifier = True

    # Check against filetype blacklist
    filetype_blacklist: List[str] = blacklist["filetype-blacklist"]
    if filetype_blacklist and message.attachments:
        for ft in message.attachments:
            for a in filetype_blacklist:
                if ft.filename.lower().endswith(a):
                    broke_blacklist = True
                    infraction_type.append(f"FileType({a})")

    # Check url blacklist
    url_blacklist = cast(Optional["re.Pattern[str]"], blacklist["url-blacklist_regex"])
    if url_blacklist is not None:
        if broke := url_blacklist.findall(LowerCaseContent):
            broke_blacklist = True
            infraction_type.append(f"URL({_formatregexfind(broke)})")

    return (broke_blacklist, notifier, infraction_type)


# Parse if we skip a message due to X reasons
def parse_skip_message(Client: discord.Client, message: discord.Message, *, allow_bots: bool = False) -> bool:
    """
    Parse to skip a message based on the author being a bot, itself, or not in a guild.
    The additional allow_bots flag will remove checking if the user is a bot if it is set to True

    :returns: bool -- Whether or not to skip the message, True being to skip
    """

    # Make sure we don't start a feedback loop.
    if message.author.id == Client.user.id:
        return True

    # only check if we are not allowing bots
    if not allow_bots:
        # Ignore message if author is a bot
        if message.author.bot:
            return True

    # Ignore messages that do not originate from a guild
    if not message.guild:
        return True

    return False


# Parse a boolean datatype from a string
def parse_boolean(instr: str) -> Union[bool, Literal[0]]:
    """
    Deprecated: use parse_boolean_strict
    Parse a boolean from preset true|false values
    Returns 0 (a falsey) if data could not be parsed
    """

    warnings.warn("parse_boolean is a deprecated function, use parse_boolean_strict instead", DeprecationWarning)

    parsed = parse_boolean_strict(instr)

    if parsed is None:
        return 0

    return parsed


def parse_boolean_strict(s: str, /) -> Optional[bool]:
    """
    Parse a boolean from preset true|false values
    Returns None (a falsey) if data could not be parsed
    If s is None this function will propagate None
    """

    yeslist: List[str] = ["yes", "true", "y", "t", "1"]
    nolist: List[str] = ["no", "false", "n", "f", "0"]

    if s.lower() in yeslist:
        return True
    elif s.lower() in nolist:
        return False

    return None


# Parse channel from message and put it into specified config
async def update_log_channel(message: discord.Message, args: list[str], client: discord.Client, log_name: str, verbose: bool = True) -> None:
    """
    Update logging channel db config with name log_name
    Handles exceptions into one exception

    :raises: errors.log_channel_update_error - Updating the channel failed
    """

    if not message.guild:
        raise errors.log_channel_update_error("ERROR: No guild")

    if not isinstance(message.channel, discord.TextChannel):
        raise errors.log_channel_update_error("ERROR: Wrong channel context")

    if args:
        log_channel_str = args[0].strip("<#!>")
    else:
        with db_hlapi(message.guild.id) as db:
            try:
                lchannel = f"<#{int(lchannel)}>" if (lchannel := db.grab_config(log_name)) else "nothing"
            except ValueError:
                await message.channel.send(f"ERROR: {log_name} is corrupt, please reset this channel config")
                raise errors.log_channel_update_error("Corrupted db location")
        await message.channel.send(f"{log_name} is set to {lchannel}")
        return

    if log_channel_str in ["remove", "rm", "delete"]:
        with db_hlapi(message.guild.id) as db:
            db.delete_config(log_name)
        await message.channel.send(f"Deleted {log_name} channel config")
        return

    try:
        log_channel = int(log_channel_str)
    except ValueError:
        await message.channel.send(constants.sonnet.error_channel.invalid)
        raise errors.log_channel_update_error("Channel is not a valid channel")

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        await message.channel.send(constants.sonnet.error_channel.invalid)
        raise errors.log_channel_update_error("Channel is not a valid channel")

    if not isinstance(discord_channel, discord.TextChannel):
        await message.channel.send(constants.sonnet.error_channel.wrongType)
        raise errors.log_channel_update_error("Channel is not a valid channel")

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send(constants.sonnet.error_channel.scope)
        raise errors.log_channel_update_error("Channel is not in guild")

    # Nothing failed so send to db
    with db_hlapi(message.guild.id) as db:
        db.add_config(log_name, str(log_channel))

    if verbose: await message.channel.send(f"Successfully updated {log_name}")


def _parse_role_perms(author: discord.Member, permrole: str) -> bool:
    return bool(permrole and bool([i.id for i in author.roles if int(permrole) == i.id]))


Permtype = Union[str, Tuple[str, Callable[[discord.Message], bool]]]


@overload
def parse_core_permissions(channel: discord.TextChannel, member: discord.Member, mconf: Dict[str, str], perms: Literal["everyone"]) -> Literal[True]:
    ...


@overload
def parse_core_permissions(channel: discord.TextChannel, member: discord.Member, mconf: Dict[str, str], perms: Literal["moderator", "administrator", "owner"]) -> bool:
    ...


@overload
def parse_core_permissions(channel: discord.TextChannel, member: discord.Member, mconf: Dict[str, str], perms: str) -> Optional[bool]:
    ...


def parse_core_permissions(channel: discord.TextChannel, member: discord.Member, mconf: Dict[str, str], perms: str) -> Optional[bool]:
    """
    Parse permissions of a given TextChannel and Member, only parses core permissions (everyone,moderator,administrator,owner) and does not have verbosity
    This is a lightweight alternative to parse_permissions for parsing simple permissions, while not sufficient for full command permission parsing.

    :returns: Optional[bool] - Has permission, or None if the perm name was not one of the core permissions
    """

    if perms == "everyone":
        return True
    elif perms == "moderator":
        default_t = channel.permissions_for(member)
        default = default_t.ban_members or default_t.administrator
        modperm = (member, mconf["moderator-role"])
        adminperm = (member, mconf["admin-role"])
        return bool(default or _parse_role_perms(*modperm) or _parse_role_perms(*adminperm))
    elif perms == "administrator":
        default = channel.permissions_for(member).administrator
        adminperm = (member, mconf["admin-role"])
        return bool(default or _parse_role_perms(*adminperm))
    elif perms == "owner":
        return bool(channel.guild.owner and member.id == channel.guild.owner.id)

    return None


# Parse user permissions to run a command
async def parse_permissions(message: discord.Message, mconf: Dict[str, str], perms: Permtype, verbose: bool = True) -> bool:
    """
    Parse the permissions of the given message object to check if they meet the required permtype
    Verbosity can be set to not print if the perm check failed

    :returns: bool
    """

    if not isinstance(message.channel, discord.TextChannel):
        # Perm check called outside a guild
        return False

    if not isinstance(message.author, discord.Member):
        if verbose:
            await message.channel.send(
                "CAUGHT ERROR: Attempted permission check on a non member object\n(This can happen if a member that is using a command leaves the server before the permission check is completed)"
                )
        return False

    you_shall_pass = False
    if isinstance(perms, (tuple, list)):
        you_shall_pass = perms[1](message)
        perms = perms[0]
    else:
        # Cast None to False (previous behavior of parse_permissions)
        you_shall_pass = parse_core_permissions(message.channel, message.author, mconf, perms) or False

    if you_shall_pass:
        return True
    else:
        if verbose:
            await message.channel.send(f"You need permissions `{perms}` to run this command")
        return False


# Returns true if any of the items in the list return true, more of an orgate
def ifgate(inlist: Iterable[Any]) -> bool:
    """
    Deprecated function to run any() over an iterable, use any() instead

    :returns: bool
    """
    warnings.warn("This function will be removed in the event of sonnet V2.0.0, use any() instead", DeprecationWarning)
    return any(inlist)


# Grab files of a message from the internal cache
def grab_files(guild_id: int, message_id: int, ramfs: lexdpyk.ram_filesystem, delete: bool = False) -> Optional[list[discord.File]]:
    """
    Grab all files from a message from the internal encryption cache

    :returns: Optional[List[discord.File]]
    """

    try:

        files = ramfs.ls(f"{guild_id}/files/{message_id}")[1]
        discord_files = []
        for i in files:

            try:

                loc = ramfs.read_f(f"{guild_id}/files/{message_id}/{i}/pointer")
                assert isinstance(loc, io.BytesIO)
                loc.seek(0)
                pointer = loc.read()

                keys = ramfs.read_f(f"{guild_id}/files/{message_id}/{i}/key")
                assert isinstance(keys, io.BytesIO)
                keys.seek(0)
                key = keys.read(32)
                iv = keys.read(16)

                name = ramfs.read_f(f"{guild_id}/files/{message_id}/{i}/name")
                assert isinstance(name, io.BytesIO)
                name.seek(0)
                fname = name.read().decode("utf8")

                try:
                    encrypted_file = encrypted_reader(pointer, key, iv)  # errors raised here
                    rawfile = lz4.frame.LZ4FrameFile(filename=encrypted_file, mode="rb")

                    dfile = io.BytesIO(rawfile.read())

                    rawfile.close()
                    encrypted_file.close()

                    discord_files.append(discord.File(dfile, filename=fname))
                except (lib_encryption_wrapper.errors.HMACInvalidError, lib_encryption_wrapper.errors.NotSonnetAESError):
                    pass

                if delete:
                    try:
                        os.remove(pointer)
                    except FileNotFoundError:
                        pass

            except FileNotFoundError:
                continue

        if delete:
            try:
                ramfs.rmdir(f"{guild_id}/files/{message_id}")
            except FileNotFoundError:
                pass

        return discord_files

    except FileNotFoundError:

        return None


# Generate a prettified reply field from a message for displaying in embeds
def generate_reply_field(message: discord.Message) -> str:
    """
    Generate a <=2048 length field containing message contents, a jump to the message, and a reply if the message was replying to another

    :returns: str -- The "message context field"
    """

    embed_lim: int = constants.embed.description
    mini_lim: int = embed_lim // 4

    # Generate replies
    jump = f"\n\n[(Link)]({message.jump_url})"
    if (r := message.reference) and (rr := r.resolved) and isinstance(rr, discord.Message):
        reply_contents = "> {} {}".format(rr.author.mention, rr.content.replace("\n", " ")) + "\n"
        if len(reply_contents) >= mini_lim:
            reply_contents = reply_contents[:mini_lim - 4] + "...\n"
    else:
        reply_contents = ""

    message_content: str = reply_contents + message.content
    if len(message_content) >= (embed_lim - len(jump)):
        message_content = message_content[:embed_lim - len(jump) - 3] + "..."
    message_content = message_content + jump

    return message_content


# Parse a role name and put it into the specified db conf
async def parse_role(message: discord.Message, args: list[str], db_entry: str, verbose: bool = True) -> int:
    """
    Parse a role from a command and put it into the db under the db_entry name

    :returns: int -- The success state of adding the role to the db, 0 being no error
    """

    if not message.guild:
        await message.channel.send("ERROR: Could not resolve guild")
        return 1

    if args:
        role_str: str = args[0].strip("<@&>")
    else:
        with db_hlapi(message.guild.id) as db:
            try:
                r_int = int(db.grab_config(db_entry) or 0)
            except ValueError:
                await message.channel.send(f"ERROR: {db_entry} is corrupt, please reset this role config")
                return 1
        await message.channel.send(f"{db_entry} is {message.guild.get_role(r_int)}")
        return 0

    if role_str in ["remove", "rm", "delete"]:
        with db_hlapi(message.guild.id) as db:
            db.delete_config(db_entry)
        await message.channel.send(f"Deleted {db_entry} role config")
        return 0

    try:
        role = message.guild.get_role(int(role_str))
    except ValueError:
        await message.channel.send(constants.sonnet.error_role.invalid)
        return 1

    if not role:
        await message.channel.send(constants.sonnet.error_role.invalid)
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config(db_entry, str(role.id))

    if verbose: await message.channel.send(f"Updated {db_entry} to {role}")

    return 0


# Grab a message object from a link or message mention
async def parse_channel_message_noexcept(message: discord.Message, args: list[str], client: discord.Client) -> tuple[discord.Message, int]:
    """
    Parse a channel message from a url, #channel messageid, or channelid-messageid field

    :returns: Tuple[discord.Message, int] -- The message and the amount of args the message grabbing took
    :raises: lib_sonnetcommands.CommandError -- The message did not exist or the function had invalid inputs
    """

    if not message.guild:
        raise lib_sonnetcommands.CommandError("ERROR: Not a guild message")

    # Capture replies first, but only use on parse errors to preserve legacy behavior
    reply_message: Optional[discord.Message] = None
    if (r := message.reference) is not None and isinstance((rr := r.resolved), discord.Message):
        reply_message = rr

    try:
        message_link = args[0].replace("-", "/").split("/")
        log_channel: Union[str, int] = message_link[-2]
        message_id = message_link[-1]
        nargs = 1
    except IndexError:
        try:
            log_channel = args[0].strip("<#!>")
            message_id = args[1]
            nargs = 2
        except IndexError:
            if reply_message is not None:
                return reply_message, 0
            raise lib_sonnetcommands.CommandError(constants.sonnet.error_args.not_enough)

    try:
        log_channel = int(log_channel)
    except ValueError:
        if reply_message is not None:
            return reply_message, 0
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_channel.invalid)

    try:
        message_id_int = int(message_id)
    except ValueError:
        if reply_message is not None:
            return reply_message, 0
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_message.invalid)

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_channel.invalid)

    if not isinstance(discord_channel, discord.TextChannel):
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_channel.scope)

    if discord_channel.guild.id != message.guild.id:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_channel.scope)

    try:
        discord_message = await discord_channel.fetch_message(message_id_int)
    except discord.errors.HTTPException:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_message.invalid)

    if not discord_message:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_message.invalid)

    return (discord_message, nargs)


async def parse_channel_message(message: discord.Message, args: List[str], client: discord.Client) -> Tuple[discord.Message, int]:
    """
    Parse a channel message from a url, #channel messageid, or channelid-messageid field

    :returns: Tuple[discord.Message, int] -- The message and the amount of args the message grabbing took
    :raises: errors.message_parse_failure -- The message did not exist or the function had invalid inputs
    """
    try:
        return await parse_channel_message_noexcept(message, args, client)
    except lib_sonnetcommands.CommandError as ce:
        await message.channel.send(ce)
        raise errors.message_parse_failure(ce)


UserInterface = Union[discord.User, discord.Member]


# should return a union of many types but for now only handle discord.Message
async def _guess_id_type(message: discord.Message, mystery_id: int) -> Optional[Union[discord.Message, discord.Role, discord.TextChannel]]:

    # hot path current channel id
    if message.channel.id == mystery_id and isinstance(message.channel, discord.TextChannel):
        return message.channel

    # asserts guild
    if not message.guild:
        return None

    # requires guild
    if (role := message.guild.get_role(mystery_id)) is not None:
        return role

    if (chan := message.guild.get_channel(mystery_id)) is not None:
        if isinstance(chan, discord.TextChannel):
            return chan

    # asserts channel
    if not isinstance(message.channel, discord.TextChannel):
        return None

    # requires channel
    try:
        if (discord_message := await message.channel.fetch_message(mystery_id)) is not None:
            return discord_message
    except discord.errors.HTTPException:
        pass

    return None


async def parse_user_member_noexcept(message: discord.Message,
                                     args: List[str],
                                     client: discord.Client,
                                     argindex: int = 0,
                                     default_self: bool = False) -> Tuple[UserInterface, Optional[discord.Member]]:
    """
    Parse a user and member object from a potential user string
    Always returns a user, only returns member if the user is in the guild
    User returned might be a member, do not rely on this.

    :returns: Tuple[Union[discord.User, discord.Member], Optional[discord.Member]] -- A discord user and optional member
    :raises: lib_sonnetcommands.CommandError -- Could not find the user or input invalid
    """

    if not message.guild or not isinstance(message.author, discord.Member):
        raise lib_sonnetcommands.CommandError("Not a guild message")

    try:
        uid = int(args[argindex].strip("<@!>"))
    except ValueError:
        raise lib_sonnetcommands.CommandError("Invalid UserID")
    except IndexError:
        if default_self:
            return message.author, message.author
        else:
            raise lib_sonnetcommands.CommandError("No user specified")

    member: Optional[discord.Member]
    user: Optional[discord.User | discord.Member]

    try:
        member = message.guild.get_member(uid)
        if not (user := client.get_user(uid)):
            user = await client.fetch_user(uid)
    except (discord.errors.NotFound, discord.errors.HTTPException):
        if (pot := await _guess_id_type(message, uid)) is not None:
            errappend = "Note: While this ID is not a valid user ID, it is "
            if isinstance(pot, discord.TextChannel):
                errappend += f"a valid channel ID: <#{pot.id}>"
            elif isinstance(pot, discord.Message):
                errappend += f"a valid message by a user with ID {pot.author.id}\n(did you mean to select this user?)"
            elif isinstance(pot, discord.Role):
                errappend += "a valid role"

            raise lib_sonnetcommands.CommandError(f"User does not exist\n{errappend}")

        raise lib_sonnetcommands.CommandError("User does not exist")

    return user, member


async def parse_user_member(message: discord.Message, args: List[str], client: discord.Client, argindex: int = 0, default_self: bool = False) -> Tuple[UserInterface, Optional[discord.Member]]:
    """
    Parse a user and member object from a potential user string
    Always returns a user, only returns member if the user is in the guild
    User returned might be a member, do not rely on this.

    :returns: tuple[discord.User | discord.Member, Optional[discord.Member]] -- A discord user and optional member
    :raises: errors.user_parse_error -- Could not find the user or input invalid
    """
    try:
        return await parse_user_member_noexcept(message, args, client, argindex=argindex, default_self=default_self)
    except lib_sonnetcommands.CommandError as ce:
        await message.channel.send(ce)
        raise errors.user_parse_error(ce)


def format_duration(durationSeconds: Union[int, float]) -> str:
    """
    Returns an end user formatted duration from a seconds duration up to decades

    :returns: str - Formatted string
    """

    fseconds = float(durationSeconds)

    # The general idea is this steps through timepoints till the number is in a low enough range to be human readable

    base = "second"
    ranges: List[Tuple[str, int]] = [("minute", 60), ("hour", 60), ("day", 24), ("year", 365), ("decade", 10)]

    for i in ranges:

        if fseconds >= i[1]:
            fseconds /= i[1]
            base = i[0]

        else:
            break

    rounded = round(fseconds, 1)

    # Basically removes a .0 if the number ends in .0
    perfectround = int(rounded) if rounded.is_integer() else rounded

    return f"{perfectround} {base}{'s'*(perfectround!=1)}"


_PT = TypeVar("_PT")


def paginate_noexcept(vals: List[_PT], page: int, per_page: int, lim: int, fmtfunc: Optional[Callable[[_PT], str]] = None) -> str:
    """
    Paginates a list of items while working around the bounds of a limit
    Optionally format with fmtfunc, otherwise str will be called on each value
    
    params:
        vals - list containing values to be appended to a single page
        page - requested page of pagination
        per_page - how many values to display per page
        lim - max length that the returning string will be
        fmtfunc - optional formatting function, otherwise str is called on _PT

    :raises: lib_sonnetcommands.CommandError - not meant to be caught, goes directly to end user
    """

    if fmtfunc is None:
        fmtfunc = lambda s: str(s)

    cpagecount = math.ceil(len(vals) / per_page)

    # Test if valid page
    if not 0 <= page < cpagecount:
        raise lib_sonnetcommands.CommandError(f"ERROR: No such page {page+1}")

    # Why can you never be happy :defeatcry:
    #
    # Implemented below is a microreallocator, every item in a page has
    # a fixed maximum length, but if one item doesn't need that length we can
    # give it to other items, so we can do a first pass to get lengths of them all,
    # pool spare space, and give it when needed
    #
    # This is similar enough to the golang method of dual pass string operations that
    # it is worth mentioning that it is in fact inspired from the go strings stdlib
    # (ultrabear) highly recommends reading it, its really well written!

    # Take slice once to avoid memcopies every iteration
    pageslice = vals[page * per_page:page * per_page + per_page]

    # This lets us store more on cases where there is less items than there should be, i/e eof
    actual_per_page = len(pageslice)

    maxlen = (lim // actual_per_page)

    # pooled will say how many spare chars we have left
    # it is calculated as pooled = sum[(maxlen - lencuritem) for i in items]
    # In this way, if pool is negative do not have enough space to not cut values off
    # If it is positive we can loop with no size limit

    itemstore = [fmtfunc(i) for i in pageslice]

    # Add +1 for newline
    lenarr = [maxlen - (len(i) + 1) for i in itemstore]

    pooled = sum(lenarr)

    # We write output using a string.Buil- wait this isn't golang
    # Whatever, this is efficient
    writer = io.StringIO()

    if pooled >= 0:
        for i in itemstore:
            writer.write(i + "\n")
    else:
        # We need to go more complicated, by only using the positive pooled we can increase the item length cap a little
        pospool = sum(i for i in lenarr if i > 0)  # Remove negatives
        newmaxlen = maxlen + (pospool // actual_per_page)  # Account for per item in our new pospool
        if newmaxlen <= 1:
            raise lib_sonnetcommands.CommandError("ERROR: The amount of items to display overflows the set possible limit with newline separators")

        for i in itemstore:
            # Cap at newmaxlen-1 and then add \n at the end
            # this ensures we always have newline separators
            writer.write(i[:newmaxlen - 1] + "\n")

    return writer.getvalue()
