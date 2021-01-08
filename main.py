# Import core systems
import os, importlib, io

# Start Discord.py
import discord

# Initialise system library for editing PATH.
import sys
# Initialise time for health monitoring.
import time
# Import Globstar library
import glob

# Get token from environment variables.
TOKEN = os.environ.get('SONNET_TOKEN') or os.environ.get('RHEA_TOKEN')

# insert at 1, 0 is the script path (or '' in REPL)
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
Client = discord.Client(
    case_insensitive=True,
    status=discord.Status.online,
    intents=intents
)

# Import libraries.
command_modules = []
command_modules_dict = {}
dynamiclib_modules = []
dynamiclib_modules_dict = {}

def sonnet_load_command_modules():
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()
    # Init imports
    for f in os.listdir('./cmds'):
        if f.startswith("cmd_") and f.endswith(".py"):
            print(f)
            command_modules.append(importlib.import_module(f[:-3]))
    for f in os.listdir("./dlibs"):
        if f.startswith("dlib_") and f.endswith(".py"):
            print(f)
            dynamiclib_modules.append(importlib.import_module(f[:-3]))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)
    for module in dynamiclib_modules:
        dynamiclib_modules_dict.update(module.commands)

sonnet_load_command_modules()


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
        if not(make_dir[0] in self.directory_table.keys()):
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

    def create_f(self, file_to_write):

        file_to_write = file_to_write.split("/")
        if len(file_to_write) > 1:
            try:
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]))
            except KeyError:
                self.mkdir("/".join(file_to_write[:-1]))
                return self.directory_table[file_to_write[0]].create_f("/".join(file_to_write[1:]))
        else:
            self.data_table[file_to_write[0]] = io.BytesIO()

        return self.data_table[file_to_write[0]]


# Initalize ramfs, kernel ramfs
ramfs = ram_filesystem()
kernel_ramfs = ram_filesystem()
# Import configs
from LeXdPyK_conf import BOT_OWNER

def regenerate_ramfs():
    global ramfs
    ramfs = ram_filesystem()

def sonnet_reload_command_modules():
    print("Reloading Kernel Modules")
    # Init vars
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules_dict = {}
    dynamiclib_modules_dict = {}
    # Update set
    for i in range(len(command_modules)):
            command_modules[i] = (importlib.reload(command_modules[i]))
    for i in range(len(dynamiclib_modules)):
            dynamiclib_modules[i] = (importlib.reload(dynamiclib_modules[i]))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)
    for module in dynamiclib_modules:
        dynamiclib_modules_dict.update(module.commands)
    # Regen tempramfs
    regenerate_ramfs()
    

# Generate debug command subset
debug_commands = {}
debug_commands["debug-modules-load"] = sonnet_load_command_modules
debug_commands["debug-modules-reload"] = sonnet_reload_command_modules
debug_commands["debug-drop-cache"] = regenerate_ramfs


# Catch errors without being fatal - log them.
@Client.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        f.write(f'Unhandled error: {args[0]}\n')
        raise


async def kernel_0(argtype):
    if argtype in dynamiclib_modules_dict.keys():
        await dynamiclib_modules_dict[argtype]( 
            client=Client, ramfs=ramfs, bot_start=bot_start_time,
            command_modules=[command_modules, command_modules_dict],
            dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
            kernel_version=version_info, kernel_ramfs=kernel_ramfs)


async def kernel_1(argtype, arg1):
    if argtype in dynamiclib_modules_dict.keys():
        await dynamiclib_modules_dict[argtype](arg1,
            client=Client, ramfs=ramfs, bot_start=bot_start_time,
            command_modules=[command_modules, command_modules_dict],
            dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
            kernel_version=version_info, kernel_ramfs=kernel_ramfs)


async def kernel_2(argtype, arg1, arg2):
    if argtype in dynamiclib_modules_dict.keys():
        await dynamiclib_modules_dict[argtype](arg1, arg2,
            client=Client, ramfs=ramfs, bot_start=bot_start_time,
            command_modules=[command_modules, command_modules_dict],
            dynamiclib_modules=[dynamiclib_modules, dynamiclib_modules_dict],
            kernel_version=version_info, kernel_ramfs=kernel_ramfs)


@Client.event
async def on_connect():
    await kernel_0("on-connect")
    
@Client.event
async def on_disconnect():
    await kernel_0("on-disconnect")

@Client.event
async def on_ready():
    await kernel_0("on-ready")

@Client.event
async def on_resumed():
    await kernel_0("on-resumed")
    
@Client.event
async def on_message(message):

    # If bot owner run a debug command
    if message.content in debug_commands.keys() and BOT_OWNER and message.author.id == int(BOT_OWNER):
        debug_commands[message.content]()
        await message.channel.send("Debug command has run")
        return

    try:
        await kernel_1("on-message", message)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message\nPlease contact bot owner")
        raise e

@Client.event
async def on_message_delete(message):
    try:
        await kernel_1("on-message-delete", message)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message-delete\nPlease contact bot owner")
        raise e

@Client.event
async def on_bulk_message_delete(messages):
    try:
        await kernel_1("on-bulk-message-delete", messages)
    except Exception as e:
        await messages[0].channel.send(f"FATAL ERROR in on-bulk-message-delete\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_message_delete(payload):
    try:
        await kernel_1("on-raw-message-delete", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send("FATAL ERROR in on-raw-message-delete\nPlease contect bot owner")
        raise e

@Client.event
async def on_raw_bulk_message_delete(payload):
    try:
        await kernel_1("on-raw-bulk-message-delete", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send("FATAL ERROR in on-raw-bulk-message-delete\nPlease contect bot owner")
        raise e

@Client.event
async def on_message_edit(old_message, message):
    try:
        await kernel_2("on-message-edit", old_message, message)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-message-edit\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_message_edit(payload):
    try:
        await kernel_1("on-raw-message-edit", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send(f"FATAL ERROR in on-raw-message-edit\nPlease contact bot owner")
        raise e


@Client.event
async def on_reaction_add(reaction, user):
    try:
        await kernel_2("on-reaction-add", reaction, user)
    except Exception as e:
        await reaction.message.channel.send(f"FATAL ERROR in on-reaction-add\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_reaction_add(payload):
    try:
        await kernel_1("on-raw-reaction-add", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send("FATAL ERROR in on-raw-reaction-add\nPlease contect bot owner")
        raise e

@Client.event
async def on_reaction_remove(reaction, user):
    try:
        await kernel_2("on-reaction-remove", reaction, user)
    except Exception as e:
        await reaction.message.channel.send(f"FATAL ERROR in on-reaction-remove\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_reaction_remove(payload):
    try:
        await kernel_1("on-raw-reaction-remove", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send("FATAL ERROR in on-raw-reaction-remove\nPlease contect bot owner")
        raise e

@Client.event
async def on_reaction_clear(message, reactions):
    try:
        await kernel_2("on-reaction-clear", message, reactions)
    except Exception as e:
        await message.channel.send(f"FATAL ERROR in on-reaction-clear\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_reaction_clear(payload):
    try:
        await kernel_1("on-raw-reaction-clear", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send(f"FATAL ERROR in on-raw-reaction-clear\nPlease contact bot owner")
        raise e

@Client.event
async def on_reaction_clear_emoji(reaction):
    try:
        await kernel_1("on-reaction-clear-emoji", reaction)
    except Exception as e:
        await reaction.message.channel.send(f"FATAL ERROR in on-reaction-clear-emoji\nPlease contact bot owner")
        raise e

@Client.event
async def on_raw_reaction_clear_emoji(payload):
    try:
        await kernel_1("on-raw-reaction-clear-emoji", payload)
    except Exception as e:
        await Client.get_channel(payload.channel_id).send("FATAL ERROR in on-raw-reaction-clear-emoji\nPlease contect bot owner")
        raise e


@Client.event
async def on_member_join(member):
    await kernel_1("on-member-join", member)

@Client.event
async def on_member_remove(member):
    await kernel_1("on-member-remove", member)

@Client.event
async def on_member_update(before, after):
    await kernel_2("on-member-update", before, after)


@Client.event
async def on_guild_join(guild):
    await kernel_1("on-guild-join", guild)

@Client.event
async def on_guild_remove(guild):
    await kernel_1("on-guild-remove", guild)

@Client.event
async def on_guild_update(before, after):
    await kernel_2("on-guild-update", before, after)


@Client.event
async def on_member_ban(guild, user):
    await kernel_2("on-member-ban", guild, user)

@Client.event
async def on_member_unban(guild, user):
    await kernel_2("on-member-unban", guild, user)


version_info = "1.1.0 'LeXdPyK'"
bot_start_time = time.time()
if TOKEN:
    Client.run(TOKEN, bot=True, reconnect=True)
else:
    print("You need a token set in SONNET_TOKEN or RHEA_TOKEN environment variables to use sonnet")


# Clear cache at exit
for i in glob.glob("datastore/*.cache.db"):
    os.remove(i)
print("\rCache Cleared, Thank you for Using Sonnet")
