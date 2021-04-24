# Parsers for message handling
# Ultrabear 2020

import importlib

import lz4.frame, discord, os, json, hashlib

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_encryption_wrapper

importlib.reload(lib_encryption_wrapper)
import sonnet_cfg

importlib.reload(sonnet_cfg)

from sonnet_cfg import REGEX_VERSION
from lib_db_obfuscator import db_hlapi
from lib_encryption_wrapper import encrypted_reader

from typing import Union, List, Tuple, Dict, Callable, Iterable, Optional, Any

re: Any = importlib.import_module(REGEX_VERSION)


class errors:
    class log_channel_update_error(RuntimeError):
        pass

    class message_parse_failure(Exception):
        pass


unicodeFilter = re.compile(r'[^a-z0-9 ]+')  # type: ignore


# Run a blacklist pass over a messages content and files
def parse_blacklist(indata: List[Any]) -> Tuple[bool, bool, List[str]]:
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

    # Check message agaist word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in text_to_blacklist.split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append(f"Word({i})")

    # Check message agaist word in word blacklist
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

    yeslist: List[str] = ["yes", "true", "y", "t", "1"]
    nolist: List[str] = ["no", "false", "n", "f", "0"]

    if instr.lower() in yeslist:
        return True
    elif instr.lower() in nolist:
        return False

    return 0


# Parse channel from message and put it into specified config
async def update_log_channel(message, args, client, log_name: str, verbose: bool = True):

    if args:
        log_channel = args[0].strip("<#!>")
    else:
        with db_hlapi(message.guild.id) as db:
            lchannel = f"<#{lchannel}>" if (lchannel := db.grab_config(log_name)) else "nothing"
        await message.channel.send(f"{log_name} is set to {lchannel}")
        raise errors.log_channel_update_error("ERROR: No Channel supplied")

    try:
        log_channel = int(log_channel)
    except ValueError:
        await message.channel.send("ERROR: Channel is not a valid int")
        raise errors.log_channel_update_error("Channel is not a valid channel")

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        await message.channel.send("ERROR: Channel is not a valid channel")
        raise errors.log_channel_update_error("Channel is not a valid channel")

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send("ERROR: Channel is not in guild")
        raise errors.log_channel_update_error("Channel is not in guild")

    # Nothing failed so send to db
    with db_hlapi(message.guild.id) as db:
        db.add_config(log_name, log_channel)

    if verbose: await message.channel.send(f"Successfully updated {log_name}")


def _parse_role_perms(message: discord.Message, permrole: discord.Role) -> bool:
    return permrole and bool([i.id for i in message.author.roles if int(permrole) == i.id])


Permtype = Union[str, Tuple[str, Callable[[discord.Message], bool]]]


# Parse user permissions to run a command
async def parse_permissions(message: discord.Message, mconf: Dict[str, str], perms: Permtype, verbose: bool = True) -> bool:

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
    elif (t := type(perms)) != str and (t == tuple or t == list):
        you_shall_pass = perms[1](message)  # type: ignore
        perms = perms[0]

    if you_shall_pass:
        return True
    else:
        if verbose:
            await message.channel.send(f"You need permissions `{perms}` to run this command")
        return False


# Returns true if any of the items in the list return true, more of an orgate
def ifgate(inlist: Iterable) -> bool:
    return any(inlist)


# Grab files of a message from the internal cache or using webrequests
def grab_files(guild_id: int, message_id: int, ramfs, delete: bool = False) -> Optional[List[discord.File]]:

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
            discord_files.append(discord.File(rawfile, filename=i))
            rawfile.close()
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

    # Generate replies
    jump = f"\n\n[(Link)]({message.jump_url})"
    if (r := message.reference) and (rr := r.resolved):
        reply_contents = "> {} {}".format(rr.author.mention, rr.content.replace("\n", " ")) + "\n"
        if len(reply_contents) >= 512:
            reply_contents = reply_contents[:512 - 4] + "...\n"
    else:
        reply_contents = ""

    message_content = reply_contents + message.content
    if len(message_content) >= (2048 - len(jump)):
        message_content = message_content[:2048 - len(jump) - 3] + "..."
    message_content = message_content + jump

    return message_content


# Parse a role name and put it into the specified db conf
async def parse_role(message: discord.Message, args: List[str], db_entry: str, verbose: bool = True):

    if args:
        role: Union[str, discord.Role] = args[0].strip("<@&>")
    else:
        with db_hlapi(message.guild.id) as db:
            await message.channel.send(f"{db_entry} is {message.guild.get_role(int(db.grab_config(db_entry) or 0))}")
        return

    try:
        role = message.guild.get_role(int(role))
    except ValueError:
        await message.channel.send("ERROR: Role is not valid int")
        return 1

    if not role:
        await message.channel.send("ERROR: Role does not exist")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config(db_entry, role.id)

    if verbose: await message.channel.send(f"Updated {db_entry} to {role}")


# Grab a message object from a link or message mention
async def parse_channel_message(message: discord.Message, args: List[str], client: discord.Client) -> Tuple[discord.Message, int]:

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
            await message.channel.send("ERROR: Not enough args supplied")
            raise errors.message_parse_failure

    try:
        log_channel = int(log_channel)
    except ValueError:
        await message.channel.send("ERROR: Channel is not a valid int")
        raise errors.message_parse_failure

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        await message.channel.send("ERROR: Channel is not a valid channel")
        raise errors.message_parse_failure

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send("ERROR: Channel is not in guild")
        raise errors.message_parse_failure

    try:
        discord_message = await discord_channel.fetch_message(int(message_id))
    except (ValueError, discord.errors.HTTPException):
        await message.channel.send("ERROR: Invalid MessageID")
        raise errors.message_parse_failure

    if not discord_message:
        await message.channel.send("ERROR: Invalid MessageID")
        raise errors.message_parse_failure

    return (discord_message, nargs)
