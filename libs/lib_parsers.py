# Parsers for message handling
# Ultrabear 2020

import importlib

import lz4.frame, discord, os, json, hashlib, io, warnings

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_encryption_wrapper

importlib.reload(lib_encryption_wrapper)
import sonnet_cfg

importlib.reload(sonnet_cfg)
import lib_constants

importlib.reload(lib_constants)

from sonnet_cfg import REGEX_VERSION
from lib_db_obfuscator import db_hlapi
from lib_encryption_wrapper import encrypted_reader
import lib_constants as constants

from typing import Union, List, Tuple, Dict, Callable, Iterable, Optional, Any
import lib_lexdpyk_h as lexdpyk

re: Any = importlib.import_module(REGEX_VERSION)


class errors:
    class log_channel_update_error(RuntimeError):
        pass

    class message_parse_failure(Exception):
        pass

    class user_parse_error(Exception):
        pass


unicodeFilter = re.compile(r'[^a-z0-9 ]+')

_parse_blacklist_inputs = Tuple[discord.Message, Dict[str, Any], lexdpyk.ram_filesystem]


# Run a blacklist pass over a messages content and files
def parse_blacklist(indata: _parse_blacklist_inputs) -> Tuple[bool, bool, List[str]]:
    """
    Deprecated, this should be in dlib_messages.py
    Parse the blacklist over a message object

    :returns: Tuple[bool, bool, List[str]] -- broke blacklist, broke notifer list, list of strings of infraction messages
    """
    message, blacklist, ramfs = indata

    # Preset values
    broke_blacklist = False
    notifier = False
    infraction_type = []

    # Compilecheck regex
    try:
        ramfs.ls(f"{message.guild.id}/regex")
    except FileNotFoundError:

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
                regexname = hex(int.from_bytes(hashlib.sha256(i.encode("utf8")).digest(), "big"))[-32:]
                ramfs.create_f(f"{message.guild.id}/regex/{regex_type}/{regexname}", f_type=re.compile, f_args=[i])

    blacklist["regex-blacklist"] = [ramfs.read_f(f"{message.guild.id}/regex/regex-blacklist/{i}") for i in ramfs.ls(f"{message.guild.id}/regex/regex-blacklist")[0]]
    blacklist["regex-notifier"] = [ramfs.read_f(f"{message.guild.id}/regex/regex-notifier/{i}") for i in ramfs.ls(f"{message.guild.id}/regex/regex-notifier")[0]]

    # If in whitelist, skip parse to save resources
    if blacklist["blacklist-whitelist"] and int(blacklist["blacklist-whitelist"]) in [i.id for i in message.author.roles]:
        return (False, False, [])

    text_to_blacklist = unicodeFilter.sub('', message.content.lower().replace(":", " ").replace("\n", " "))

    # Check message against word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in text_to_blacklist.split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append(f"Word({i})")

    # Check message against word in word blacklist
    word_blacklist = blacklist["word-in-word-blacklist"]
    if word_blacklist:
        for i in word_blacklist:
            if i in text_to_blacklist.replace(" ", ""):
                broke_blacklist = True
                infraction_type.append(f"WordInWord({i})")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        try:
            if (broke := i.findall(message.content.lower())):  # type: ignore
                broke_blacklist = True
                infraction_type.append(f"RegEx({', '.join(broke)})")
        except re.error:
            pass  # GC for old regex

    # Check message against REGEXP notifier list
    regex_blacklist = blacklist["regex-notifier"]
    for i in regex_blacklist:
        if i.findall(message.content.lower()):  # type: ignore
            notifier = True

    # Check against filetype blacklist
    filetype_blacklist = blacklist["filetype-blacklist"]
    if filetype_blacklist and message.attachments:
        for i in message.attachments:
            for a in filetype_blacklist:
                if i.filename.lower().endswith(a):  # type: ignore
                    broke_blacklist = True
                    infraction_type.append(f"FileType({a})")

    return (broke_blacklist, notifier, infraction_type)


# Parse if we skip a message due to X reasons
def parse_skip_message(Client: discord.Client, message: discord.Message) -> bool:
    """
    Parse to skip a message based on the author being a bot, itself, or not in a guild

    :returns: bool -- Whether or not to skip the message, True being to skip
    """

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return True

    # Ignore message if author is a bot
    if message.author.bot:
        return True

    # Ignore dmmessage
    if not message.guild:
        return True

    return False


# Parse a boolean datatype from a string
def parse_boolean(instr: str) -> Union[bool, int]:
    """
    Parse a boolean from preset true|false values
    Returns 0 (a falsey) if data could not be parsed
    """

    yeslist: List[str] = ["yes", "true", "y", "t", "1"]
    nolist: List[str] = ["no", "false", "n", "f", "0"]

    if instr.lower() in yeslist:
        return True
    elif instr.lower() in nolist:
        return False

    return 0


# Parse channel from message and put it into specified config
async def update_log_channel(message: discord.Message, args: List[str], client: discord.Client, log_name: str, verbose: bool = True) -> None:
    """
    Update logging channel db config with name log_name
    Handles exceptions into one exception

    :raises: errors.log_channel_update_error
    """


    if args:
        log_channel_str = args[0].strip("<#!>")
    else:
        with db_hlapi(message.guild.id) as db:
            lchannel = f"<#{lchannel}>" if (lchannel := db.grab_config(log_name)) else "nothing"
        await message.channel.send(f"{log_name} is set to {lchannel}")
        raise errors.log_channel_update_error(constants.sonnet.error_channel.none)

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

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send(constants.sonnet.error_channel.scope)
        raise errors.log_channel_update_error("Channel is not in guild")

    # Nothing failed so send to db
    with db_hlapi(message.guild.id) as db:
        db.add_config(log_name, str(log_channel))

    if verbose: await message.channel.send(f"Successfully updated {log_name}")


def _parse_role_perms(message: discord.Message, permrole: discord.Role) -> bool:
    return permrole and bool([i.id for i in message.author.roles if int(permrole) == i.id])


Permtype = Union[str, Tuple[str, Callable[[discord.Message], bool]]]


# Parse user permissions to run a command
async def parse_permissions(message: discord.Message, mconf: Dict[str, str], perms: Permtype, verbose: bool = True) -> bool:
    """
    Parse the permissions of the given member object to check if they meet the required permtype
    Verbosity can be set to not print if the perm check failed

    :returns: bool
    """

    if not message.author.guild:
        if verbose:
            await message.channel.send(
                "CAUGHT ERROR: Attempted permission check on a non member object\n(This can happen if a member that is using a command leaves the server before the permission check is completed)"
                )
        return False

    you_shall_pass = False
    if perms == "everyone":
        you_shall_pass = True
    elif perms == "moderator":
        default = message.author.permissions_in(message.channel).ban_members
        modperm = (message, mconf["moderator-role"])
        adminperm = (message, mconf["admin-role"])
        you_shall_pass = default or _parse_role_perms(*modperm) or _parse_role_perms(*adminperm)
    elif perms == "administrator":
        default = message.author.permissions_in(message.channel).administrator
        adminperm = (message, mconf["admin-role"])
        you_shall_pass = default or _parse_role_perms(*adminperm)
    elif perms == "owner":
        you_shall_pass = message.author.id == message.channel.guild.owner.id
    elif isinstance(perms, (tuple, list)):
        you_shall_pass = perms[1](message)
        perms = perms[0]

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


# Grab files of a message from the internal cache or using webrequests
def grab_files(guild_id: int, message_id: int, ramfs: lexdpyk.ram_filesystem, delete: bool = False) -> Optional[List[discord.File]]:
    """
    Grab all files from a message from the internal encryption cache

    :returns: Optional[List[discord.File]]
    """

    try:

        files = ramfs.ls(f"{guild_id}/files/{message_id}")[1]
        discord_files = []
        for i in files:

            loc = ramfs.read_f(f"{guild_id}/files/{message_id}/{i}/pointer")
            loc.seek(0)
            pointer = loc.read()

            keys = ramfs.read_f(f"{guild_id}/files/{message_id}/{i}/key")
            keys.seek(0)
            key = keys.read(32)
            iv = keys.read(16)

            encrypted_file = encrypted_reader(pointer, key, iv)
            rawfile = lz4.frame.LZ4FrameFile(filename=encrypted_file, mode="rb")

            dfile = io.BytesIO(rawfile.read())

            rawfile.close()
            encrypted_file.close()

            discord_files.append(discord.File(dfile, filename=i))

            if delete:
                try:
                    os.remove(pointer)
                except FileNotFoundError:
                    pass

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
    if (r := message.reference) and (rr := r.resolved):
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
async def parse_role(message: discord.Message, args: List[str], db_entry: str, verbose: bool = True) -> int:
    """
    Parse a role from a command and put it into the db under the db_entry name

    :returns: int -- The success state of adding the role to the db, 0 being no error
    """


    if args:
        role_str: str = args[0].strip("<@&>")
    else:
        with db_hlapi(message.guild.id) as db:
            await message.channel.send(f"{db_entry} is {message.guild.get_role(int(db.grab_config(db_entry) or 0))}")
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
        db.add_config(db_entry, role.id)

    if verbose: await message.channel.send(f"Updated {db_entry} to {role}")

    return 0


# Grab a message object from a link or message mention
async def parse_channel_message(message: discord.Message, args: List[str], client: discord.Client) -> Tuple[discord.Message, int]:
    """
    Parse a channel message from a url, #channel messageid, or channelid-messageid field

    :returns: Tuple[discord.Message, int] -- The message and the amount of args the message grabbing took
    :raises: errors.message_parse_failure -- The message did not exist or the function had invalid inputs
    """

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
            await message.channel.send(constants.sonnet.error_args.not_enough)
            raise errors.message_parse_failure

    try:
        log_channel = int(log_channel)
    except ValueError:
        await message.channel.send(constants.sonnet.error_channel.invalid)
        raise errors.message_parse_failure

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        await message.channel.send(constants.sonnet.error_channel.invalid)
        raise errors.message_parse_failure

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send(constants.sonnet.error_channel.scope)
        raise errors.message_parse_failure

    try:
        discord_message = await discord_channel.fetch_message(int(message_id))
    except (ValueError, discord.errors.HTTPException):
        await message.channel.send(constants.sonnet.error_message.invalid)
        raise errors.message_parse_failure

    if not discord_message:
        await message.channel.send(constants.sonnet.error_message.invalid)
        raise errors.message_parse_failure

    return (discord_message, nargs)


async def parse_user_member(message: discord.Message, args: List[str], client: discord.Client, argindex: int = 0, default_self: bool = False) -> Tuple[discord.User, Optional[discord.Member]]:
    """
    Parse a user and member object from a potential user string
    Always returns a user, only returns member if the user is in the guild
    User returned might be a member, do not rely on this.

    :returns: Tuple[discord.User, Optional[discord.Member]] -- A discord user and optional member
    :raises: errors.user_parse_error -- Could not find the user or input invalid
    """

    member: discord.Member
    user: discord.User

    try:
        member = message.guild.get_member(int(args[argindex].strip("<@!>")))
        if not (user := client.get_user(int(args[argindex].strip("<@!>")))):
            user = await client.fetch_user(int(args[argindex].strip("<@!>")))
    except ValueError:
        await message.channel.send("Invalid UserID")
        raise errors.user_parse_error("Invalid User")
    except IndexError:
        if default_self:
            member = message.author
            user = message.author
        else:
            await message.channel.send("No user specified")
            raise errors.user_parse_error("No user specified")
    except (discord.errors.NotFound, discord.errors.HTTPException):
        await message.channel.send("User does not exist")
        raise errors.user_parse_error("User does not exist")

    return user, member
