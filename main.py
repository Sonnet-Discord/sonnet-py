# Intro
print("Booting LeXdPyK")

# Import core systems
import os, importlib, sys, io, time

# Import sub dependencies
import glob, json, hashlib, logging, getpass

# Start Discord.py
import discord, asyncio

# Start Logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Get token from environment variables.
TOKEN = os.environ.get('SONNET_TOKEN') or os.environ.get('RHEA_TOKEN')

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
Client = discord.Client(case_insensitive=True, status=discord.Status.online, intents=intents)


# Define token encryption system "miniflip"
class miniflip:
    def __init__(self, password):
        key = hashlib.sha512(password.encode("utf8")).digest()
        self._width = 8
        self._passkey = [int.from_bytes(key[i:i + self._width], "little") for i in range(0, len(key), self._width)]

    def _btod(self, data):
        return [int.from_bytes(data[i:i + self._width], "little") for i in range(0, len(data), self._width)]

    def _dtob(self, data):
        out = []
        for chunk in data:
            out.extend([(chunk >> (8 * i) & 0xff) for i in range(self._width)])
        return bytes(out)

    def _encrypt(self, data: bytes):
        data = self._btod(data)
        for i in self._passkey:
            data = [chunk ^ i for chunk in data]
        return self._dtob(data)

    def _decrypt(self, data: bytes):
        data = self._btod(data)
        for i in self._passkey[::-1]:
            data = [i ^ chunk for chunk in data]
        return self._dtob(data)

    def encrypt(self, data: str):

        if type(data) != str: raise TypeError(f"encrypt only accepts type 'str', not type `{type(data).__name__}`")

        data = data.encode("utf8")

        data = self._encrypt(data)[::-1]
        data = self._encrypt(data)
        data = self._encrypt(data)[::-1]

        return data

    def decrypt(self, data: bytes):

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
    def __init__(self):
        self.directory_table = {}
        self.data_table = {}

    def __enter__(self):
        return self

    def mkdir(self, make_dir):

        # Make fs list
        make_dir = make_dir.split("/")

        # If the current dir doesnt exist then create it
        if not (make_dir[0] in self.directory_table.keys()):
            self.directory_table[make_dir[0]] = ram_filesystem()

        # If there is more directory left then keep going
        if len(make_dir) > 1:
            return self.directory_table[make_dir[0]].mkdir("/".join(make_dir[1:]))
        else:
            return self

    def remove_f(self, remove_item):

        remove_item = remove_item.split("/")
        if len(remove_item) > 1:
            return self.directory_table[remove_item[0]].remove_f("/".join(remove_item[1:]))
        else:
            try:
                del self.data_table[remove_item[0]]
                return self
            except KeyError:
                raise FileNotFoundError("File does not exist")

    def read_f(self, file_to_open):

        file_to_open = file_to_open.split("/")
        try:
            if len(file_to_open) > 1:
                return self.directory_table[file_to_open[0]].read_f("/".join(file_to_open[1:]))
            else:
                return self.data_table[file_to_open[0]]
        except KeyError:
            raise FileNotFoundError("File does not exist")

    def create_f(self, file_to_write, f_type=io.BytesIO, f_args=[]):

        file_to_write = file_to_write.split("/")
        if len(file_to_write) > 1:
            try:
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]), f_type=f_type, f_args=f_args)
            except KeyError:
                self.mkdir("/".join(file_to_write[:-1]))
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]), f_type=f_type, f_args=f_args)
        else:
            self.data_table[file_to_write[0]] = f_type(*f_args)

        return self.data_table[file_to_write[0]]

    def rmdir(self, directory_to_delete):

        directory_to_delete = directory_to_delete.split("/")
        try:
            if len(directory_to_delete) > 1:
                self.directory_table[directory_to_delete[0]].rmdir("/".join(directory_to_delete[1:]))
            else:
                del self.directory_table[directory_to_delete[0]]
        except KeyError:
            raise FileNotFoundError("Folder does not exist")

    def ls(self, *folderpath):

        try:
            if folderpath:
                folderpath = folderpath[0].split("/")
                if len(folderpath) > 1:
                    return self.directory_table[folderpath[0]].ls("/".join(folderpath[1:]))
                else:
                    return self.directory_table[folderpath[0]].ls()
            else:
                return [list(self.data_table.keys()), list(self.directory_table.keys())]
        except KeyError:
            raise FileNotFoundError("Filepath does not exist")

    def tree(self, *folderpath):
        try:
            if folderpath:
                folderpath = folderpath[0].split("/")
                if len(folderpath) > 1:
                    return self.directory_table[folderpath[0]].tree("/".join(folderpath[1:]))
                else:
                    return self.directory_table[folderpath[0]].tree()
            else:
                datamap = [list(self.data_table.keys()), {}]
                for folder in self.directory_table.keys():
                    datamap[1][folder] = self.directory_table[folder].tree()
                return datamap

        except KeyError:
            raise FileNotFoundError("Filepath does not exist")


# Import blacklist
try:
    with open("common/blacklist.json", "r") as blacklist_file:
        blacklist = json.load(blacklist_file)
except FileNotFoundError:
    blacklist = {"guild": [], "user": []}
    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)

# Define debug commands

command_modules = []
command_modules_dict = {}
dynamiclib_modules = []
dynamiclib_modules_dict = {}

# Initalize ramfs, kernel ramfs
ramfs = ram_filesystem()
kernel_ramfs = ram_filesystem()


# Define kernel syntax error
class KernelSyntaxError(SyntaxError):
    pass


# Import configs
from LeXdPyK_conf import BOT_OWNER

if (t := type(BOT_OWNER)) == str or t == int:
    BOT_OWNER = [int(BOT_OWNER)] if BOT_OWNER else []
elif BOT_OWNER:
    BOT_OWNER = [int(i) for i in BOT_OWNER]


def kernel_load_command_modules(*args):
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()

    # Init return state
    err = []

    # Init imports
    for f in filter(lambda f: f.startswith("cmd_") and f.endswith(".py"), os.listdir('./cmds')):
        print(f)
        try:
            command_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append([e, f[:-3]])
    for f in filter(lambda f: f.startswith("dlib_") and f.endswith(".py"), os.listdir("./dlibs")):
        print(f)
        try:
            dynamiclib_modules.append(importlib.import_module(f[:-3]))
        except Exception as e:
            err.append([e, f[:-3]])

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

    if err: return ("\n".join([f"Error importing {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])


def regenerate_ramfs(*args):
    global ramfs
    ramfs = ram_filesystem()


def regenerate_kernel_ramfs(*args):
    global kernel_ramfs
    kernel_ramfs = ram_filesystem()


def kernel_reload_command_modules(*args):
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


def kernel_blacklist_guild(*args):

    try:
        blacklist["guild"].append(int(args[0][0]))
    except (ValueError, IndexError):
        return ["Asking value is not INT", []]

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_blacklist_user(*args):

    try:
        blacklist["user"].append(int(args[0][0]))
    except (ValueError, IndexError):
        return ["Asking value is not INT", []]

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_unblacklist_guild(*args):

    try:
        if int(args[0][0]) in blacklist["guild"]:
            del blacklist["guild"][blacklist["guild"].index(int(args[0][0]))]
        else:
            return ["Item is not blacklisted", []]
    except (ValueError, IndexError):
        return ["Asking value is not INT", []]

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_unblacklist_user(*args):

    try:
        if int(args[0][0]) in blacklist["user"]:
            del blacklist["user"][blacklist["user"].index(int(args[0][0]))]
        else:
            return ["Item is not blacklisted", []]
    except (ValueError, IndexError):
        return ["Asking value is not INT", []]

    with open("common/blacklist.json", "w") as blacklist_file:
        json.dump(blacklist, blacklist_file)


def kernel_logout(*args):
    asyncio.create_task(Client.close())


def kernel_drop_dlibs(*args):
    global dynamiclib_modules, dynamiclib_modules_dict
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}


def kernel_drop_cmds(*args):
    global command_modules, command_modules_dict
    command_modules = []
    command_modules_dict = {}


def logging_toggle(*args):
    if logger.isEnabledFor(10):
        logger.setLevel(20)
        return ["Logging at L20", []]
    else:
        logger.setLevel(10)
        return ["Logging at L10", []]


# Generate debug command subset
debug_commands = {}
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
    def __init__(self, err, argtype):
        self.err = err
        owner = f"<@!{BOT_OWNER[0]}>" if BOT_OWNER else "BOT OWNER"
        self.errmsg = f"FATAL ERROR in {argtype}\nPlease contact {owner}\nErr: `{type(err).__name__}: {err}`"


# Catch errors.
@Client.event
async def on_error(event, *args, **kwargs):
    raise


async def do_event(event, args):
    await dynamiclib_modules_dict[event](
        *args,
        client=Client,
        ramfs=ramfs,
        bot_start=bot_start_time,
        command_modules=[command_modules, command_modules_dict],
        dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
        kernel_version=version_info,
        kernel_ramfs=kernel_ramfs
        )


async def event_call(argtype, *args):

    etypes = []

    try:
        if argtype in dynamiclib_modules_dict.keys():
            await do_event(argtype, args)
    except Exception as e:
        etypes.append(errtype(e, argtype))

    call = 0
    while (exname := f"{argtype}-{call}") in dynamiclib_modules_dict.keys():
        try:
            await do_event(exname, args)
        except Exception as e:
            etypes.append(errtype(e, exname))

        call += 1

    if etypes:
        return etypes[0]
    else:
        return None


async def safety_check(guild=None, guild_id=None, user=None, user_id=None):

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
            await guild.ban(user, reason="LeXdPyK: SYSTEM LEVEL BLACKLIST")
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


@Client.event
async def on_connect():
    if e := await event_call("on-connect"):
        raise e.err


@Client.event
async def on_disconnect():
    if e := await event_call("on-disconnect"):
        raise e.err


@Client.event
async def on_ready():
    if e := await event_call("on-ready"):
        raise e.err


@Client.event
async def on_resumed():
    if e := await event_call("on-resumed"):
        raise e.err


@Client.event
async def on_message(message):

    args = message.content.split(" ")

    # If bot owner run a debug command
    if len(args) >= 2 and args[0] in debug_commands.keys() and message.author.id in BOT_OWNER and args[1] == str(Client.user.id):
        if e := debug_commands[args[0]](args[2:]):
            await message.channel.send(e[0])
            if e[1]: raise e[1][0]
        else:
            await message.channel.send("Debug command returned no error status")
            return

    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-message", message):
            await message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_message_delete(message):
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-message-delete", message):
            await message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_bulk_message_delete(messages):
    if await safety_check(guild=messages[0].guild, user=messages[0].author):
        if e := await event_call("on-bulk-message-delete", messages):
            await messages[0].channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_message_delete(payload):
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-message-delete", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_bulk_message_delete(payload):
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-bulk-message-delete", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_message_edit(old_message, message):
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-message-edit", old_message, message):
            await message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_message_edit(payload):
    if e := await event_call("on-raw-message-edit", payload):
        await Client.get_channel(payload.channel_id).send(e.errmsg)
        raise e.err


@Client.event
async def on_reaction_add(reaction, user):
    if await safety_check(guild=reaction.message.guild, user=user):
        if e := await event_call("on-reaction-add", reaction, user):
            await reaction.message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_reaction_add(payload):
    if await safety_check(guild_id=payload.guild_id, user_id=payload.user_id):
        if e := await event_call("on-raw-reaction-add", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_reaction_remove(reaction, user):
    if await safety_check(guild=reaction.message.guild, user=user):
        if e := await event_call("on-reaction-remove", reaction, user):
            await reaction.message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_reaction_remove(payload):
    if await safety_check(guild_id=payload.guild_id, user_id=payload.user_id):
        if e := await event_call("on-raw-reaction-remove", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_reaction_clear(message, reactions):
    if await safety_check(guild=message.guild, user=message.author):
        if e := await event_call("on-reaction-clear", message, reactions):
            await message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_reaction_clear(payload):
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-reaction-clear", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_reaction_clear_emoji(reaction):
    if await safety_check(guild=reaction.message.guild):
        if e := await event_call("on-reaction-clear-emoji", reaction):
            await reaction.message.channel.send(e.errmsg)
            raise e.err


@Client.event
async def on_raw_reaction_clear_emoji(payload):
    if await safety_check(guild_id=payload.guild_id):
        if e := await event_call("on-raw-reaction-clear-emoji", payload):
            await Client.get_channel(payload.channel_id).send(e.errmsg)
            raise e.err


@Client.event
async def on_member_join(member):
    if await safety_check(user=member, guild=member.guild):
        if e := await event_call("on-member-join", member): raise e.err


@Client.event
async def on_member_remove(member):
    if await safety_check(guild=member.guild):
        if e := await event_call("on-member-remove", member): raise e.err


@Client.event
async def on_member_update(before, after):
    if await safety_check(user=before, guild=before.guild):
        if e := await event_call("on-member-update", before, after): raise e.err


@Client.event
async def on_guild_join(guild):
    if await safety_check(guild=guild):
        if e := await event_call("on-guild-join", guild): raise e.err


@Client.event
async def on_guild_remove(guild):
    if e := await event_call("on-guild-remove", guild): raise e.err


@Client.event
async def on_guild_update(before, after):
    if await safety_check(guild=before):
        if e := await event_call("on-guild-update", before, after): raise e.err


@Client.event
async def on_member_ban(guild, user):
    if await safety_check(guild=guild):
        if e := await event_call("on-member-ban", guild, user): raise e.err


@Client.event
async def on_member_unban(guild, user):
    if await safety_check(guild=guild, user=user):
        if e := await event_call("on-member-unban", guild, user): raise e.err


# Define version info and start time
version_info = "LeXdPyK 1.3.1"
bot_start_time = time.time()

# Start bot
if TOKEN:
    try:
        Client.run(TOKEN, bot=True, reconnect=True)
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
