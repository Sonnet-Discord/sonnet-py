# Version printing tools
# Ultrabear 2020

import importlib

import discord
import sys
import io
import time

import lib_loaders

importlib.reload(lib_loaders)
import lib_goparsers

importlib.reload(lib_goparsers)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)

from lib_loaders import clib_exists, DotHeaders, datetime_unix

from typing import List, Any, Union
import lib_lexdpyk_h as lexdpyk


# Pretty gives spacing between key-value items to have them padded
def prettyprint(inlist: List[List[str]]) -> List[str]:

    maxln = 0

    for i in inlist:
        if len(i[0]) > maxln:
            maxln = len(i[0])

    return [(f"{i[0]}{(maxln-len(i[0]))*' '} : {i[1]}") for i in inlist]


# Adds zero padding to number
def zpad(n: int) -> str:
    """
    Deprecated, just use a format string directly
    """
    return f"{n:02d}"


def getdelta(past: Union[int, float]) -> str:
    """
    Formats a delta between a past time and now to be human readable
    """

    trunning = (datetime_unix(int(time.time())) - datetime_unix(int(past)))

    seconds = trunning.seconds % 60
    minutes = ((trunning.seconds) // 60 % 60)
    hours = ((trunning.seconds) // (60 * 60))
    days = trunning.days

    hms = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    # if days is 0 dont bother rendering it
    if days == 0: return hms

    return f"{days} Day{'s'*(days != 1)}, {hms}"


async def print_version_info(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    bot_start_time: float = kwargs["bot_start"]
    dlib_modules: List[lexdpyk.dlib_module] = kwargs["dlibs"]
    modules: List[lexdpyk.cmd_module] = kwargs["cmds"]

    base_versions = []
    base_versions.append(["Python", sys.version.split(" ")[0]])
    base_versions.append(["Wrapper", discord.__version__])
    base_versions.append(["Kernel", kwargs['main_version']])
    base = "\n".join(prettyprint(base_versions))

    fmt = io.StringIO()

    fmt.write(f"```py\n{base}\n\nEvent Modules:\n")

    for a in prettyprint([[i.category_info['name'], i.version_info] for i in dlib_modules]):
        fmt.write(f"  {a}\n")

    fmt.write("\nCommand Modules:\n")

    for a in prettyprint([[i.category_info['pretty_name'], i.version_info] for i in modules]):
        fmt.write(f"  {a}\n")

    fmt.write(f"\nC  accel: {DotHeaders.version}={clib_exists}\n")

    fmt.write(f"Go accel: {lib_goparsers.GetVersion()}={lib_goparsers.hascompiled}\n")

    fmt.write(f"\nBot Uptime: {getdelta(bot_start_time)}\n```")

    content = fmt.getvalue()

    if len(content) <= 2000:
        await message.channel.send(content)
    else:
        await message.channel.send("ERROR: Exeeded discord message length limits, tell a developer to stop being lazy about rendering this")


async def uptime(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    await message.channel.send(getdelta(kwargs["bot_start"]))


async def print_stats(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    kernel_ramfs = kwargs["kernel_ramfs"]

    statistics_file = kernel_ramfs.read_f(f"{message.guild.id}/stats")
    global_statistics_file = kernel_ramfs.read_f("global/stats")

    guild_total = 0
    global_total = 0

    for i in statistics_file:
        guild_total += statistics_file[i]

    for i in global_statistics_file:
        global_total += global_statistics_file[i]

    outputmap = []

    outputmap.append(["This Guild:", "Count:"])
    for i in statistics_file:
        outputmap.append([i, statistics_file[i]])

    outputmap.append(["", ""])

    outputmap.append(["Globally:", "Count:"])
    for i in global_statistics_file:
        outputmap.append([i, global_statistics_file[i]])

    # Declare here cause fstrings cant have \ in it 草
    newline = "\n"

    writer = io.StringIO()

    writer.write(f"```py\n{newline.join(prettyprint(outputmap))}\n")

    writer.write(f"\nThis guild has sent {round(1000*(guild_total/global_total))/10}% ({guild_total}/{global_total}) of total processed events since boot```")

    await message.channel.send(writer.getvalue())


category_info = {'name': 'version', 'pretty_name': 'Version', 'description': 'Information about the current sonnet version'}

commands = {
    'version': {
        'alias': 'version-info'
        },
    'versions': {
        'alias': 'version-info'
        },
    'version-info': {
        'pretty_name': 'version-info',
        'description': 'Prints version info on sonnet modules',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': print_version_info
        },
    'uptime': {
        'pretty_name': 'uptime',
        'description': 'Prints uptime',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': uptime
        },
    'stats': {
        'alias': 'statistics'
        },
    'statistics': {
        'pretty_name': 'statistics',
        'description': 'Prints stats about messages',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': print_stats
        }
    }

version_info: str = "1.2.9-DEV"
