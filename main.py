# Check to ensure we don't import this file
if __name__ != "__main__":
    import warnings
    warnings.warn("LeXdPyK is not meant to be imported")

# Measure boot time
import time

kernel_start = time.monotonic()

# Intro
print("Booting LeXdPyK")

# Import core systems
import os, importlib, sys, io, traceback

# Import sub dependencies
import glob, json, hashlib, logging, getpass, datetime, argparse

# Import typing support
from typing import List, Optional, Any, Tuple, Dict, Union, Type, Protocol

# Start Discord.py
import discord, asyncio

# Initialize logger
logger = logging.getLogger('discord')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

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

# Initialize Discord Client.
Client = discord.Client(status=discord.Status.online, intents=intents)

# Define development mode flag
DEVELOPMENT_MODE = False


# Define token encryption system "miniflip"
class miniflip:
    __slots__ = "_width", "_passkey"

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

        data = indata.encode("utf8")

        data = self._encrypt(data)[::-1]
        data = self._encrypt(data)
        data = self._encrypt(data)[::-1]

        return data

    def decrypt(self, data: bytes) -> Optional[str]:

        data = self._decrypt(data)[::-1]
        data = self._decrypt(data)
        data = self._decrypt(data)[::-1]

        try:
            return data.rstrip(b"\x00").decode("utf8")
        except UnicodeDecodeError:
            return None


# Define ramfs
class ram_filesystem:
    __slots__ = "data_table", "directory_table"

    def __init__(self) -> None:
        self.directory_table: Dict[str, "ram_filesystem"] = {}
        self.data_table: Dict[str, object] = {}

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

    def _get_directory(self, dir_path: List[str]) -> "ram_filesystem":
        """
        Gets a directory from a dir entry or raises FileNotFoundError
        Expects last item in dir path is a directory
        """

        path: "ram_filesystem" = self

        for item in dir_path:

            try:
                path = path.directory_table[item]
            except KeyError:
                raise FileNotFoundError(f"No such folder: {'/'.join(dir_path)}")

        return path

    def mkdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":

        # Make fs list
        make_dir = self._parsedirlist(dirstr, dirlist)

        path: "ram_filesystem" = self

        for item in make_dir:
            # If the current dir doesn't exist then create it
            try:
                path = path.directory_table[item]
            except KeyError:
                path.directory_table[item] = path = ram_filesystem()

        return path

    def remove_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":
        """
        Deletes provided file location, raises on error
        """

        remove_item = self._parsedirlist(dirstr, dirlist)

        if remove_item:
            path = self._get_directory(remove_item[:-1])

            try:
                del path.data_table[remove_item[-1]]
            except KeyError:
                raise FileNotFoundError(f"No such file: {'/'.join(remove_item)}")
        else:
            raise FileNotFoundError("No file parameter passed")

        return path

    def read_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        file_to_open = self._parsedirlist(dirstr, dirlist)

        if file_to_open:
            path = self._get_directory(file_to_open[:-1])

            try:
                return path.data_table[file_to_open[-1]]
            except KeyError:
                raise FileNotFoundError("No such filepath: {'/'.join(file_to_open)}")
        else:
            raise FileNotFoundError("No file parameter passed")

    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Type[Any]] = None, f_args: Optional[List[Any]] = None) -> Any:

        if f_type is None:
            f_type = io.BytesIO

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

        path = self._get_directory(self._parsedirlist(dirstr, dirlist, allowNone=True))

        return list(path.data_table), list(path.directory_table)

    def tree(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        path = self._get_directory(self._parsedirlist(dirstr, dirlist, allowNone=True))

        datamap: Tuple[List[str], Dict[str, Any]] = (list(path.data_table), {})

        for folder in path.directory_table:
            datamap[1][folder] = path.directory_table[folder].tree()

        return datamap

    def _dump_data(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:

        path = self._get_directory(self._parsedirlist(dirstr, dirlist, True))

        try:
            filelist: List[Tuple[str, str, object]] = []

            for f in path.data_table:
                # pretty print binary files
                if isinstance(v := path.data_table[f], io.BytesIO):
                    v.seek(0)
                    filelist.append((f, type(path.data_table[f]).__name__, v.read()), )
                else:
                    filelist.append((f, type(path.data_table[f]).__name__, (path.data_table[f])), )

            datamap: Tuple[List[Any], Dict[str, Any]] = (filelist, {})

            for folder in path.directory_table:
                datamap[1][folder] = path.directory_table[folder]._dump_data()

            return datamap

        except KeyError:
            raise FileNotFoundError("Filepath does not exist")


# Import blacklist
try:
    with open("common/blacklist.json", "r", encoding="utf-8") as blacklist_file:
        blacklist = json.load(blacklist_file)

    # Ensures blacklist properly init
    assert isinstance(blacklist["guild"], list)
    assert isinstance(blacklist["user"], list)

except FileNotFoundError:
    blacklist = {"guild": [], "user": []}
    with open("common/blacklist.json", "w", encoding="utf-8") as blacklist_file:
        json.dump(blacklist, blacklist_file)

# Define debug commands
command_modules: List[Any] = []
command_modules_dict: Dict[str, Any] = {}
dynamiclib_modules: List[Any] = []
dynamiclib_modules_dict: Dict[str, Any] = {}
# LeXdPyK 1.5: undefined exec order feature
# on-message is now Dict[on-message: [[on-message items], [on-message-0 items], [on-message-1 items]]
# this feature means you can have multiple on-message calls that will exec in an undefined order, but on-message-0 will always
#  exec after on-message and on-message-1 after that etc
#  this allows flexibility with multiple modules that just "must run after command processor init"
dynamiclib_modules_exec_dict: Dict[str, List[List[Any]]] = {}


def add_module_to_exec_dict(module_dlibs: Dict[str, Any]) -> None:

    global dynamiclib_modules_exec_dict

    for k, v in module_dlibs.items():

        if (maybe_num := k.split("-")[-1]).isnumeric():
            true_key = "-".join(k.split("-")[:-1])
            idx = int(maybe_num) + 1

        else:
            true_key = k
            idx = 0

        if idx >= 2048:
            raise RuntimeError("Command execution order request exceeds 2048 (oom safety limit reached)")

        try:
            data_list = dynamiclib_modules_exec_dict[true_key]
        except KeyError:
            data_list = dynamiclib_modules_exec_dict[true_key] = []

        if len(data_list) < (idx + 1):
            data_list.extend([] for _ in range((idx + 1) - len(data_list)))

        data_list[idx].append(v)


def compress_exec_dict() -> None:

    global dynamiclib_modules_exec_dict

    for k in dynamiclib_modules_exec_dict:

        dynamiclib_modules_exec_dict[k] = [i for i in dynamiclib_modules_exec_dict[k] if i]


# Initialize ramfs, kernel ramfs
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


def log_kernel_info(s: object) -> None:
    """
    Logs kernel messages to stdout and the info logger
    """

    now_t = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(f"{now_t}: {s}")

    logger.info(f"{version_info}: {s}")


def kernel_load_command_modules(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Loading Kernel Modules")
    start_load_modules = time.monotonic()
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict, dynamiclib_modules_exec_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    dynamiclib_modules_exec_dict = {}
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
            add_module_to_exec_dict(module.commands)
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append((KernelSyntaxError("Missing commands"), module.__name__), )

    compress_exec_dict()

    log_kernel_info(f"Loaded Kernel Modules in {(time.monotonic()-start_load_modules)*1000:.1f}ms")

    if err: return ("\n".join([f"Error importing {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])
    else: return None


def regenerate_ramfs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Regenerating ramfs")
    global ramfs
    ramfs = ram_filesystem()
    return None


def regenerate_kernel_ramfs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Regenerating kernel ramfs")
    global kernel_ramfs
    kernel_ramfs = ram_filesystem()
    return None


def kernel_reload_command_modules(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Reloading Kernel Modules")
    # Init vars
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules_dict = {}
    dynamiclib_modules_dict = {}

    start_reload_modules = time.monotonic()

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
            add_module_to_exec_dict(module.commands)
            dynamiclib_modules_dict.update(module.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), module.__name__])

    # Regen tempramfs
    regenerate_ramfs()

    compress_exec_dict()

    log_kernel_info(f"Reloaded Kernel Modules in {(time.monotonic()-start_reload_modules)*1000:.1f}ms")

    if err: return ("\n".join([f"Error reimporting {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])
    else: return None


def kernel_blacklist_guild(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info(f"Attempting to blacklist guild with args {args}")

    try:
        blacklist["guild"].append(int(args[0]))
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w", encoding="utf-8") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_blacklist_user(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info(f"Attempting to blacklist user with args {args}")

    try:
        blacklist["user"].append(int(args[0]))
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w", encoding="utf-8") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_unblacklist_guild(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info(f"Attempting to unblacklist guild with args {args}")

    try:
        if int(args[0]) in blacklist["guild"]:
            del blacklist["guild"][blacklist["guild"].index(int(args[0]))]
        else:
            return "Item is not blacklisted", []
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w", encoding="utf-8") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_unblacklist_user(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info(f"Attempting to unblacklist user with args {args}")

    try:
        if int(args[0]) in blacklist["user"]:
            del blacklist["user"][blacklist["user"].index(int(args[0]))]
        else:
            return "Item is not blacklisted", []
    except (ValueError, IndexError):
        return "Asking value is not INT", []

    with open("common/blacklist.json", "w", encoding="utf-8") as blacklist_file:
        json.dump(blacklist, blacklist_file)

    return None


def kernel_logout(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Logging out of discord client session")
    asyncio.create_task(Client.close())
    return None


def kernel_drop_dlibs(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Dropping dynamiclib modules")
    global dynamiclib_modules, dynamiclib_modules_dict
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    return None


def kernel_drop_cmds(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
    log_kernel_info("Dropping command modules")
    global command_modules, command_modules_dict
    command_modules = []
    command_modules_dict = {}
    return None


def logging_toggle(args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:

    is_debug = logger.isEnabledFor(logging.DEBUG)

    log_kernel_info(f"Swapping log visibility to {'INFO' if is_debug else 'DEBUG'}")

    if is_debug:
        logger.setLevel(logging.INFO)
        return "Logging at L20 (INFO)", []
    else:
        logger.setLevel(logging.DEBUG)
        return "Logging at L10 (DEBUG)", []


class DebugCallable(Protocol):
    def __call__(self, args: List[str] = []) -> Optional[Tuple[str, List[Exception]]]:
        return None


# Generate debug command subset
debug_commands: Dict[str, DebugCallable] = {
    "debug-add-guild-blacklist": kernel_blacklist_guild,
    "debug-add-user-blacklist": kernel_blacklist_user,
    "debug-remove-guild-blacklist": kernel_unblacklist_guild,
    "debug-remove-user-blacklist": kernel_unblacklist_user,
    "debug-modules-load": kernel_load_command_modules,
    "debug-modules-reload": kernel_reload_command_modules,
    "debug-logout-system": kernel_logout,
    "debug-drop-ramfs": regenerate_ramfs,
    "debug-drop-kramfs": regenerate_kernel_ramfs,
    "debug-drop-modules": kernel_drop_dlibs,
    "debug-drop-commands": kernel_drop_cmds,
    "debug-toggle-logging": logging_toggle,
    }


# A object used to pass error messages from the kernel callers to the event handlers
class errtype:
    __slots__ = "err", "errmsg"

    def __init__(self, err: Exception, argtype: str):

        self.err = err
        owner: str = f"<@!{BOT_OWNER[0]}>" if BOT_OWNER else "BOT OWNER"
        # truncate to 1k chars to clip message to reasonable length, this makes message print to discord even if it is oversize
        # the alternative is messages too large not being accepted by discord and causing a error in kernel handling code
        # full error message can be obtained from err.log/stderr so this should be fine
        self.errmsg = f"FATAL ERROR in {argtype}\nPlease contact {owner}\nErr: `{type(err).__name__}: {err}`"[:1000]

        log_kernel_info("".join(traceback.format_exception(type(self.err), self.err, self.err.__traceback__)))

        # accept penalty of fopen syscall because errors should not be frequent and deleting/moving logs may be needed
        with open("err.log", "a+", encoding="utf-8") as logfile:
            logfile.write(f"AT {datetime.datetime.now(datetime.timezone.utc).isoformat()}:\n")
            logfile.write("".join(traceback.format_exception(type(self.err), self.err, self.err.__traceback__)))


# KeyError sentinel so we don't catch KeyError
class KernelKeyError(KeyError):
    pass


# Catch errors
@Client.event
async def on_error(event: str, *args: Any, **kwargs: Any) -> None:
    raise


async def do_event_return_error(event: Any, args: Tuple[Any, ...]) -> Optional[Exception]:
    try:

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
        return None
    except Exception as e:
        return e


async def event_call(argtype: str, *args: Any) -> Optional[errtype]:

    # used by dev mode
    tstartexec = time.monotonic()

    etypes = []

    try:
        functions = dynamiclib_modules_exec_dict[argtype]
    except KeyError:
        functions = []

    for ftable in functions:
        tasks = [asyncio.create_task(do_event_return_error(func, args)) for func in ftable]

        for i in tasks:
            if e := (await i):
                etypes.append(errtype(e, argtype))

    if DEVELOPMENT_MODE:
        log_kernel_info(f"EVENT {argtype} : {round((time.monotonic()-tstartexec)*100000)/100}ms CC {len(functions)}")

    if etypes:
        return etypes[0]
    else:
        return None


async def safety_check(guild: Optional[discord.Guild] = None, guild_id: Optional[int] = None, user: Optional[Union[discord.User, discord.Member]] = None, user_id: Optional[int] = None) -> bool:

    if guild: guild_id = guild.id
    if user: user_id = user.id
    non_null_guild: discord.Guild

    if user_id and user_id in blacklist["user"] and guild_id:

        try:
            user = await Client.fetch_user(user_id)
        except discord.errors.HTTPException:
            return False

        try:
            non_null_guild = await Client.fetch_guild(guild_id)
        except discord.errors.HTTPException:
            return False

        try:
            await non_null_guild.ban(user, reason="LeXdPyK: SYSTEM LEVEL BLACKLIST", delete_message_days=0)
        except discord.errors.Forbidden:

            # call kernel_blacklist_guild to add to json db, blacklist guild
            # because it must be controlled by user that is blacklisted if there are no perms
            kernel_blacklist_guild([str(guild_id)])
            try:
                await non_null_guild.leave()
                return False
            except discord.errors.HTTPException:
                pass

        except discord.errors.HTTPException:
            return False

        return False

    if guild_id and guild_id in blacklist["guild"]:

        try:
            non_null_guild = await Client.fetch_guild(guild_id)
        except discord.errors.HTTPException:
            return False

        try:
            await non_null_guild.leave()
            return False
        except discord.errors.HTTPException:
            pass

        return False

    return True


async def sendable_send(sendable: object, message: str) -> None:
    if isinstance(sendable, (discord.TextChannel, discord.DMChannel)):
        try:
            await sendable.send(message)
        except discord.errors.HTTPException:
            pass


@Client.event
async def on_connect() -> None:
    log_kernel_info(f"Connection to discord established {(time.monotonic()-kernel_start):.2f}s after boot")
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
    if len(args) >= 2 and args[0] in debug_commands:
        if message.author.id in BOT_OWNER and args[1].strip("<@!>") == str(Client.user.id):
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


def gentoken() -> str:

    TOKEN = getpass.getpass("Enter TOKEN: ")

    passwd = getpass.getpass("Enter TOKEN password: ")
    if passwd != getpass.getpass("Confirm TOKEN password: "):
        print("ERROR: passwords do not match")
        raise ValueError

    with open(".tokenfile", "wb") as tokenfile:
        encryptor = miniflip(passwd)
        tokenfile.write(encryptor.encrypt(TOKEN))

    return TOKEN


# Main function, handles userland startup
def main(args: List[str]) -> int:

    parser = argparse.ArgumentParser()
    parser.add_argument("--log-debug", action="store_true", help="makes the logging module start in debug mode")
    parser.add_argument("--generate-token", action="store_true", help="discards the current token file if there is one, and generates a new encrypted tokenfile")
    parser.add_argument("--version", "-v", action="store_true", help="print version info and exit")
    parser.add_argument("--development", "--dev", action="store_true", help="enables development mode (prints event handling and dumps ramfs on exit), may cause performance issues")
    parsed = parser.parse_args()

    global DEVELOPMENT_MODE
    DEVELOPMENT_MODE = parsed.development

    if parsed.version:
        import platform
        pyver = f"{platform.python_implementation()} {platform.python_version()}"
        print(f"{version_info} @ {os.getcwd()}\n{pyver} @ {sys.executable}")
        return 0

    if DEVELOPMENT_MODE:
        print("Running in development mode (extra performance logging enabled)")

    # Set Loglevel
    loglevel = logging.DEBUG if parsed.log_debug else logging.INFO
    logger.setLevel(loglevel)

    # Get token from environment variables.
    TOKEN: Optional[str] = os.environ.get('SONNET_TOKEN') or os.environ.get('RHEA_TOKEN')

    # Generate tokenfile
    if parsed.generate_token:
        try:
            TOKEN = gentoken()
        except ValueError:
            return 1

    # Load token
    if TOKEN is None and os.path.isfile(".tokenfile"):
        tokenfile = open(".tokenfile", "rb")
        encryptor = miniflip(getpass.getpass("Enter TOKEN password: "))
        TOKEN = encryptor.decrypt(tokenfile.read())
        tokenfile.close()
        if TOKEN is None:
            print("Invalid TOKEN password")
            return 1

    # Load command modules
    if e := kernel_load_command_modules():
        print(e[0])

    # Start bot
    if TOKEN:
        try:
            Client.run(TOKEN, reconnect=True)
        except discord.errors.LoginFailure:
            print("Invalid token passed")
            return 1
    else:
        print("You need a token set in SONNET_TOKEN or RHEA_TOKEN environment variables, or a encrypted token in .tokenfile, to use sonnet")
        return 1

    if DEVELOPMENT_MODE:
        print("Dumping ramfs:")
        print(ramfs._dump_data())
        print("Dumping kramfs:")
        print(kernel_ramfs._dump_data())

    # Clear cache at exit
    for i in glob.glob("datastore/*.cache.db"):
        os.remove(i)

    print("\rCache Cleared, Thank you for Using Sonnet")

    return 0


# Define version info and start time
version_info: str = "LeXdPyK 1.5"
bot_start_time: float = time.time()

if __name__ == "__main__":
    print(f"Booted kernel in {(time.monotonic()-kernel_start)*1000:.0f}ms")
    sys.exit(main(sys.argv))
