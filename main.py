# Check to ensure we dont import this file
if __name__ != "__main__": raise ImportError("LeXdPyK is not meant to be imported")

# Intro
print("Booting LeXdPyK")

# Import core systems
import os, importlib, sys, io, time, traceback

# Import sub dependencies
import glob, json, hashlib, logging, getpass, datetime

# Import typing support
from typing import List, Optional, Any, Tuple, Dict, Union, Type, Protocol

# Start Discord.py
import discord, asyncio

# Start Logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Get token from environment variables.
TOKEN: Optional[str] = os.environ.get('SONNET_TOKEN') or os.environ.get('RHEA_TOKEN')

# Initialize kernel workspace
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')
sys.path.insert(1, os.getcwd() + '/dlibs')

intents = discord.Intents.default()
intents.typing = False
intents.presences = True
intents.guilds = True
intents.members = True
intents.reactions = True

# Initialise Discord Client.
Client = discord.Client(status=discord.Status.online, intents=intents)


# Define token encryption system "miniflip"
class miniflip:
    def __init__(self, password: str):
        key = hashlib.sha512(password.encode("utf8")).digest()
        self._width = 8
        self._passkey = [int.from_bytes(key[i:i + self._width], "little") for i in range(0, len(key), self._width)]

    def _btod(self, data: bytes) -> List[int]:
        return [int.from_bytes(data[i:i + self._width], "little") for i in range(0, len(data), self._width)]

    def _dtob(self, data: List[int]) -> bytes:
        out = []
        for chunk in data:
            out.extend([(chunk >> (8 * i) & 0xff) for i in range(self._width)])
        return bytes(out)

    def _encrypt(self, data: bytes) -> bytes:
        ndata = self._btod(data)
        for i in self._passkey:
            ndata = [chunk ^ i for chunk in ndata]
        return self._dtob(ndata)

    def _decrypt(self, data: bytes) -> bytes:
        ndata = self._btod(data)
        for i in self._passkey[::-1]:
            ndata = [i ^ chunk for chunk in ndata]
        return self._dtob(ndata)

    def encrypt(self, indata: str) -> bytes:

        if type(indata) != str: raise TypeError(f"encrypt only accepts type 'str', not type `{type(indata).__name__}`")

        data: bytes = indata.encode("utf8")

        data = self._encrypt(data)[::-1]
        data = self._encrypt(data)
        data = self._encrypt(data)[::-1]

        return data

    def decrypt(self, data: bytes) -> Optional[str]:

        if type(data) != bytes: raise TypeError(f"decrypt only accepts type 'bytes', not type `{type(data).__name__}`")

        data = self._decrypt(data)[::-1]
        data = self._decrypt(data)
        data = self._decrypt(data)[::-1]

        try:
            return data.rstrip(b"\x00").decode("utf8")
        except UnicodeDecodeError:
            return None


# Define ramfs
class ram_filesystem:
    def __init__(self) -> None:
        self.directory_table: Dict[str, "ram_filesystem"] = {}
        self.data_table: Dict[str, Any] = {}

    def __enter__(self) -> "ram_filesystem":
        return self

    def _parsedirlist(self, dirstr: Optional[str], dirlist: Optional[List[str]], allowNone: bool = False) -> List[str]:

        if dirlist is None and dirstr is not None:
            return dirstr.split("/")
        elif dirlist is not None:
            return dirlist
        elif allowNone:
            return []

        raise TypeError("No dirstr or dirlist passed")

    def mkdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":

        # Make fs list
        make_dir = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for item in make_dir:
            # If the current dir doesnt exist then create it
            try:
                path = path.directory_table[item]
            except KeyError:
                path.directory_table[item] = path = ram_filesystem()

        return path

    def remove_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        remove_item = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for i, item in enumerate(remove_item):

            try:
                if i < len(remove_item) - 1:
                    path = path.directory_table[item]
                else:
                    del path.data_table[item]
            except KeyError:
                raise FileNotFoundError(f"No such filepath: {'/'.join(remove_item)}")

        return path

    def read_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        file_to_open = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for i, item in enumerate(file_to_open):

            try:
                if i < len(file_to_open) - 1:
                    path = path.directory_table[item]
                else:
                    return path.data_table[item]
            except KeyError:
                raise FileNotFoundError("No such filepath: {'/'.join(file_to_open)}")

    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Type[Any]] = None, f_args: Optional[List[Any]] = None) -> Any:

        f_type = io.BytesIO if f_type is None else f_type
        f_args = [] if f_args is None else f_args

        file_to_write = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for i, item in enumerate(file_to_write):

            if i < len(file_to_write) - 1:
                try:
                    path = path.directory_table[item]
                except KeyError:
                    path.directory_table[item] = path = ram_filesystem()
            else:
                f = path.data_table[item] = f_type(*f_args)
                return f

    def rmdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:

        directory_to_delete = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for i, item in enumerate(directory_to_delete):

            try:
                if i < len(directory_to_delete) - 1:
                    path = path.directory_table[item]
                else:
                    del path.directory_table[item]
            except KeyError:
                raise FileNotFoundError(f"No such filepath: {'/'.join(directory_to_delete)}")

    def ls(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:

        folderpath = self._parsedirlist(dirstr, dirlist, allowNone=True)

        path: "ram_filesystem" = self

        for item in folderpath:

            try:
                path = path.directory_table[item]
            except KeyError:
                raise FileNotFoundError(f"No such filepath: {'/'.join(folderpath)}")

        return list(path.data_table), list(path.directory_table)

    def tree(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        folderpath = self._parsedirlist(dirstr, dirlist, allowNone=True)

        path: "ram_filesystem" = self

        for item in folderpath:

            try:
                path = path.directory_table[item]
            except KeyError:
                raise FileNotFoundError(f"No such filepath: {'/'.join(folderpath)}")

        datamap: Tuple[List[str], Dict[str, Any]] = (list(path.data_table), {})

        for folder in path.directory_table:
            datamap[1][folder] = path.directory_table[folder].tree()

        return datamap


# Import blacklist
try:
    with open("common/blacklist.json", "r") as blacklist_file:
        blacklist = json.load(blacklist_file)
except FileNotFoundError:
    blacklist = {"guild": [], "user": []}
    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

# Define debug commands

command_modules: List[Any] = []
command_modules_dict: Dict[str, Any] = {}
dynamiclib_modules: List[Any] = []
dynamiclib_modules_dict: Dict[str, Any] = {}

# Initalize ramfs, kernel ramfs
ramfs = ram_filesystem()
kernel_ramfs = ram_filesystem()


# Define kernel syntax error
class KernelSyntaxError(SyntaxError):
    pass


# Import configs
from LeXdPyK_conf import BOT_OWNER as KNOWN_OWNER

UNKNOWN_OWNER: Any = KNOWN_OWNER
BOT_OWNER: List[int]

if isinstance(UNKNOWN_OWNER, (str, int)):
    BOT_OWNER = [int(UNKNOWN_OWNER)] if UNKNOWN_OWNER else []
elif isinstance(UNKNOWN_OWNER, (list, tuple)):
    BOT_OWNER = [int(i) for i in UNKNOWN_OWNER]
else:
    BOT_OWNER = []


def kernel_load_command_modules(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()

    # Init return state
    err: List[Tuple[Exception, str]] = []

    # Init imports
    for f in filter(lambda f: f.startswith("cmd_") and f.endswith(".py"), os.listdir('./cmds')):
        print(f)
        try:
            command_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append((e, f[:-3]), )
    for f in filter(lambda f: f.startswith("dlib_") and f.endswith(".py"), os.listdir("./dlibs")):
        print(f)
        try:
            dynamiclib_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append((e, f[:-3]), )

    # Update hashmaps
    for module in command_modules:
        try:
            command_modules_dict.update(module.commands)
        except AttributeError:
            err.append((KernelSyntaxError("Missing commands"), module.__name__), )
    for module in dynamiclib_modules:
        try:
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append((KernelSyntaxError("Missing commands"), module.__name__), )

    if err: return ("\n".join([f"Error importing {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])
    else: return None


def regenerate_ramfs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    global ramfs
    ramfs = ram_filesystem()
    return None


def regenerate_kernel_ramfs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    global kernel_ramfs
    kernel_ramfs = ram_filesystem()
    return None


def kernel_reload_command_modules(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    print("Reloading Kernel Modules")
    # Init vars
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules_dict = {}
    dynamiclib_modules_dict = {}

    # Init ret state
    err = []

    # Update set
    for i in range(len(command_modules)):
        try:
            command_modules[i] = (importlib.reload(command_modules[i]))
        except Exception as e:
            err.append([e, command_modules[i].__name__])
    for i in range(len(dynamiclib_modules)):
        try:
            dynamiclib_modules[i] = (importlib.reload(dynamiclib_modules[i]))
        except Exception as e:
            err.append([e, dynamiclib_modules[i].__name__])

    # Update hashmaps
    for module in command_modules:
        try:
            command_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])
    for module in dynamiclib_modules:
        try:
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])

    # Regen tempramfs
    regenerate_ramfs()

    if err: return ("\n".join([f"Error reimporting {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])
    else: return None


def kernel_blacklist_guild(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:

    try:
        blacklist["guild"].append(int(args[0]))
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_blacklist_user(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:

    try:
        blacklist["user"].append(int(args[0]))
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_unblacklist_guild(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:

    try:
        if int(args[0]) in blacklist["guild"]:
            del blacklist["guild"][blacklist["guild"].index(int(args[0]))]
        else:
            return "Item is not blacklisted", []
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_unblacklist_user(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:

    try:
        if int(args[0]) in blacklist["user"]:
            del blacklist["user"][blacklist["user"].index(int(args[0]))]
        else:
            return "Item is not blacklisted", []
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_logout(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    asyncio.create_task(Client.close())
    return None


def kernel_drop_dlibs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    global dynamiclib_modules, dynamiclib_modules_dict
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    return None


def kernel_drop_cmds(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    global command_modules, command_modules_dict
    command_modules = []
    command_modules_dict = {}
    return None


def logging_toggle(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    if logger.isEnabledFor(10):
        logger.setLevel(20)
        return "Logging at L20", []
    else:
        logger.setLevel(10)
        return "Logging at L10", []


class DebugCallable(Protocol):
    def __call__(self, args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
        return None


# Generate debug command subset
debug_commands: Dict[str, DebugCallable] = {}
debug_commands["debug-add-guild-blacklist"] = kernel_blacklist_guild
debug_commands["debug-add-user-blacklist"] = kernel_blacklist_user
debug_commands["debug-remove-guild-blacklist"] = kernel_unblacklist_guild
debug_commands["debug-remove-user-blacklist"] = kernel_unblacklist_user
debug_commands["debug-modules-load"] = kernel_load_command_modules
debug_commands["debug-modules-reload"] = kernel_reload_command_modules
debug_commands["debug-logout-system"] = kernel_logout
debug_commands["debug-drop-ramfs"] = regenerate_ramfs
debug_commands["debug-drop-kramfs"] = regenerate_kernel_ramfs
debug_commands["debug-drop-modules"] = kernel_drop_dlibs
debug_commands["debug-drop-commands"] = kernel_drop_cmds
debug_commands["debug-toggle-logging"] = logging_toggle

# Generate tokenfile
if len(sys.argv) >= 2 and "--generate-token" in sys.argv:
    tokenfile = open(".tokenfile", "wb")
    encryptor = miniflip(getpass.getpass("Enter TOKEN password: "))
    tokenfile.write(encryptor.encrypt(TOKEN := getpass.getpass("Enter TOKEN: ")))
    tokenfile.close()

# Load token
if not TOKEN and os.path.isfile(".tokenfile"):
    tokenfile = open(".tokenfile", "rb")
    encryptor = miniflip(getpass.getpass("Enter TOKEN password: "))
    TOKEN = encryptor.decrypt(tokenfile.read())
    tokenfile.close()
    if not TOKEN:
        print("Invalid TOKEN password")
        sys.exit(1)

# Load command modules
if e := kernel_load_command_modules():
    print(e[0])


# A object used to pass error messages from the kernel callers to the event handlers
class errtype:
    def __init__(self, err: Exception, argtype: str):

        self.err = err
        owner: str = f"<@!{BOT_OWNER[0]}>" if BOT_OWNER else "BOT OWNER"
        self.errmsg = f"FATAL ERROR in {argtype}\nPlease contact {owner}\nErr: `{type(err).__name__}: {err}`"

        traceback.print_exception(type(self.err), self.err, self.err.__traceback__)

        with open("err.log", "a+") as logfile:
            logfile.write(f"AT {time.strftime('%a, %d %b %Y %H:%M:%S', datetime.datetime.now(datetime.timezone.utc).utctimetuple())}:\n")
            logfile.write("".join(traceback.format_exception(type(self.err), self.err, self.err.__traceback__)))


# KeyError sentinel so we dont catch KeyError
class KernelKeyError(KeyError):
    pass


# Catch errors
@Client.event
async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
    raise


async def do_event(event: Any, args: Tuple[Any, ...]) -> None:
    await event(
        *args,
        client=Client,
        ramfs=ramfs,
        bot_start=bot_start_time,
        command_modules=[command_modules, command_modules_dict],
        dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
        kernel_version=version_info,
        kernel_ramfs=kernel_ramfs
        )


async def event_call(argtype: str, *args: Any) -> Optional[errtype]:

    etypes = []

    try:

        # Do hash lookup with KeyError
        # Seperate from running function so we do not catch a KeyError deeper in the stack
        try:
            func = dynamiclib_modules_dict[argtype]
        except KeyError:
            raise KernelKeyError

        await do_event(func, args)

    # Check for KernelKeyError before checking for Exception (inherits from)
    except KernelKeyError:
        pass
    except Exception as e:
        etypes.append(errtype(e, argtype))

    call = 0
    while True:

        exname = f"{argtype}-{call}"

        # If there is no hash then break the loop
        try:
            func = dynamiclib_modules_dict[exname]
        except KeyError:
            break

        try:
            await do_event(func, args)
        except Exception as e:
            etypes.append(errtype(e, exname))

        call += 1

    if etypes:
        return etypes[0]
    else:
        return None


async def safety_check(guild: Optional[discord.Guild] = None, guild_id: Optional[int] = None, user: Optional[Union[discord.User, discord.Member]] = None, user_id: Optional[int] = None) -> bool:

    if guild: guild_id = guild.id
    if user: user_id = user.id

    if user_id and user_id in blacklist["user"] and guild_id:

        try:
            user = await Client.fetch_user(user_id)
        except discord.errors.HTTPException:
            return False

        try:
            guild = await Client.fetch_guild(guild_id)
        except discord.errors.HTTPException:
            return False

        try:
            await guild.ban(user, reason="LeXdPyK: SYSTEM LEVEL BLACKLIST", delete_message_days=0)
        except discord.errors.Forbidden:

            blacklist["guild"].append(guild_id)
            try:
                await guild.leave()
                return False
            except discord.errors.HTTPException:
                pass

        except discord.errors.HTTPException:
            return False

        return False

    if guild_id and guild_id in blacklist["guild"]:

        try:
            guild = await Client.fetch_guild(guild_id)
        except discord.errors.HTTPException:
            return False

        try:
            await guild.leave()
            return False
        except discord.errors.HTTPException:
            pass

        return False

    return True


async def sendable_send(sendable: Any, message: str) -> None:
    if isinstance(sendable, (discord.TextChannel, discord.DMChannel)):
        try:
            await sendable.send(message)
        except discord.errors.HTTPException:
            pass


@Client.event
async def on_connect() -> None:
    await event_call("on-connect")


@Client.event
async def on_disconnect() -> None:
    await event_call("on-disconnect")


@Client.event
async def on_ready() -> None:
    await event_call("on-ready")


@Client.event
async def on_resumed() -> None:
    await event_call("on-resumed")


@Client.event
async def on_message(message: discord.Message) -> None:

    args = message.content.split(" ")

    # If bot owner run a debug command
    if len(args) >= 2 and args[0] in debug_commands and message.author.id in BOT_OWNER and args[1] == str(Client.user.id):
        if e := debug_commands[args[0]](args[2:]):
            await message.channel.send(e[0])
            for i in e[1]:
                errtype(i, "")
        else:
            await sendable_send(message.channel, "Debug command returned no error status")
            return

    if await safety_check(guild=message.guild, user=message.author):
        if err := await event_call("on-message", message):
            await sendable_send(message.channel, err.errmsg)


@Client.event
async def on_message_delete(message: discord.Message) -> None:
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-message-delete", message):
            await sendable_send(message.channel, e.errmsg)


@Client.event
async def on_bulk_message_delete(messages: List[discord.Message]) -> None:
    if await safety_check(guild=messages[0].guild, user=messages[0].author):
        if e := await event_call("on-bulk-message-delete", messages):
            await sendable_send(messages[0].channel, e.errmsg)


@Client.event
async def on_raw_message_delete(payload: discord.RawMessageDeleteEvent) -> None:
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-message-delete", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_raw_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent) -> None:
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-bulk-message-delete", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_message_edit(old_message: discord.Message, message: discord.Message) -> None:
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-message-edit", old_message, message):
            await sendable_send(message.channel, e.errmsg)


@Client.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent) -> None:
    if e := await event_call("on-raw-message-edit", payload):
        await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_reaction_add(reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
    if await safety_check(guild=reaction.message.guild, user=user):
        if e := await event_call("on-reaction-add", reaction, user):
            await sendable_send(reaction.message.channel, e.errmsg)


@Client.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent) -> None:
    if await safety_check(guild_id=payload.guild_id, user_id=payload.user_id):
        if e := await event_call("on-raw-reaction-add", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_reaction_remove(reaction: discord.Reaction, user: Union[discord.Member, discord.User]) -> None:
    if await safety_check(guild=reaction.message.guild, user=user):
        if e := await event_call("on-reaction-remove", reaction, user):
            await sendable_send(reaction.message.channel, e.errmsg)


@Client.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent) -> None:
    if await safety_check(guild_id=payload.guild_id, user_id=payload.user_id):
        if e := await event_call("on-raw-reaction-remove", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_reaction_clear(message: discord.Message, reactions: List[discord.Reaction]) -> None:
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-reaction-clear", message, reactions):
            await sendable_send(message.channel, e.errmsg)


@Client.event
async def on_raw_reaction_clear(payload: discord.RawReactionClearEvent) -> None:
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-reaction-clear", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_reaction_clear_emoji(reaction: discord.Reaction) -> None:
    if await safety_check(guild=reaction.message.guild):
        if e := await event_call("on-reaction-clear-emoji", reaction):
            await sendable_send(reaction.message.channel, e.errmsg)


@Client.event
async def on_raw_reaction_clear_emoji(payload: discord.RawReactionClearEvent) -> None:
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-reaction-clear-emoji", payload):
            await sendable_send(Client.get_channel(payload.channel_id), e.errmsg)


@Client.event
async def on_member_join(member: discord.Member) -> None:
    if await safety_check(user=member, guild=member.guild):
        await event_call("on-member-join", member)


@Client.event
async def on_member_remove(member: discord.Member) -> None:
    if await safety_check(guild=member.guild):
        await event_call("on-member-remove", member)


@Client.event
async def on_member_update(before: discord.Member, after: discord.Member) -> None:
    if await safety_check(user=before, guild=before.guild):
        await event_call("on-member-update", before, after)


@Client.event
async def on_guild_join(guild: discord.Guild) -> None:
    if await safety_check(guild=guild):
        await event_call("on-guild-join", guild)


@Client.event
async def on_guild_remove(guild: discord.Guild) -> None:
    await event_call("on-guild-remove", guild)


@Client.event
async def on_guild_update(before: discord.Guild, after: discord.Guild) -> None:
    if await safety_check(guild=before):
        await event_call("on-guild-update", before, after)


@Client.event
async def on_member_ban(guild: discord.Guild, user: discord.User) -> None:
    if await safety_check(guild=guild):
        await event_call("on-member-ban", guild, user)


@Client.event
async def on_member_unban(guild: discord.Guild, user: discord.User) -> None:
    if await safety_check(guild=guild, user=user):
        await event_call("on-member-unban", guild, user)


# Define version info and start time
version_info: str = "LeXdPyK 1.4.3"
bot_start_time: float = time.time()

# Start bot
if TOKEN:
    try:
        Client.run(TOKEN, reconnect=True)
    except discord.errors.LoginFailure:
        print("Invalid token passed")
        sys.exit(1)
else:
    print("You need a token set in SONNET_TOKEN or RHEA_TOKEN environment variables, or a encrypted token in .tokenfile, to use sonnet")
    sys.exit(1)

# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
