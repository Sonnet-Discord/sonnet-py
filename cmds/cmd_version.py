# Version printing tools
# Ultrabear 2020

import importlib

import discord
from datetime import datetime
import sys

import lib_loaders

importlib.reload(lib_loaders)

from lib_loaders import clib_exists, DotHeaders


def prettyprint(inlist):

    maxln = 0

    for i in inlist:
        if len(i[0]) > maxln:
            maxln = len(i[0])

    return [(f"{i[0]}{(maxln-len(i[0]))*' '} : {i[1]}") for i in inlist]


def zpad(innum):
    return (2 - len(str(innum))) * "0" + str(innum)


def getdelta(past):

    trunning = (datetime.utcnow() - datetime.utcfromtimestamp(past))

    seconds = trunning.seconds % 60
    minutes = ((trunning.seconds) // 60 % 60)
    hours = ((trunning.seconds) // (60 * 60))

    return f"{trunning.days} Day{'s'*(trunning.days != 1)}, {zpad(hours)}:{zpad(minutes)}:{zpad(seconds)}"


async def print_version_info(message, args, client, **kwargs):

    bot_start_time = kwargs["bot_start"]
    dlib_modules = kwargs["dlibs"]
    modules = kwargs["cmds"]

    base_versions = []
    base_versions.append(["Python", sys.version.split(" ")[0]])
    base_versions.append(["Discord.py", discord.__version__])
    base_versions.append(["Kernel", kwargs['main_version']])
    base = "\n".join(prettyprint(base_versions))

    fmt = f"```py\n{base}\n\nEvent Modules:\n"

    for a in prettyprint([[i.category_info['name'], i.version_info] for i in dlib_modules]):
        fmt += f"  {a}\n"

    fmt += "\nCommand Modules:\n"

    for a in prettyprint([[i.category_info['pretty_name'], i.version_info] for i in modules]):
        fmt += f"  {a}\n"

    fmt += f"\nC accel: {DotHeaders.version}={clib_exists}\n"

    fmt += f"\nBot Uptime: {getdelta(bot_start_time)}\n```"

    await message.channel.send(fmt)


async def uptime(message, args, client, **kwargs):

    await message.channel.send(getdelta(kwargs["bot_start"]))


async def print_stats(message, args, client, **kwargs):

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
    [outputmap.append([i, statistics_file[i]]) for i in statistics_file]

    outputmap.append(["", ""])

    outputmap.append(["Globally:", "Count:"])
    [outputmap.append([i, global_statistics_file[i]]) for i in global_statistics_file]

    newline = "\n"

    fmt = f"```py\n{newline.join(prettyprint(outputmap))}\n"

    fmt += f"\nThis guild has sent {round(1000*(guild_total/global_total))/10}% ({guild_total}/{global_total}) of total processed events since boot```"

    await message.channel.send(fmt)


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

version_info = "1.2.2"
