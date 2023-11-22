# Scripting engine to use sonnet commands
# Inspired by MantaroBots unix like commands
# And a lot of boredom :]
# Ultrabear 2021

import asyncio
import copy as pycopy
import io
import shlex
import time

import discord

import lib_sonnetcommands

from typing import Any, Dict, List, Set, Tuple

import lib_lexdpyk_h as lexdpyk
from lib_parsers import parse_permissions, parse_channel_message_noexcept
from lib_sonnetcommands import CommandCtx, SonnetCommand, cache_sweep
from lib_datetimeplus import Time

# This was placed after the exponential expansion exploit was found
# to help reduce severity if future exploits are found
#
# A limit of 200 will reasonably never be reached by a normal user
# It was previously 1000, but that is too high
exec_lim = 200

# This was placed after children were given moderator perms
# If sonnetsh/map/amap exceeds a runtime of around 3 minutes it will stop processing
#
# This limit may be reached, but it is unlikely in normal operations
runtime_lim_secs = 60 * 3

# Set of message ids scheduled to end task
killed_message_ids: Set[int] = set()


def kill_this_task(message: discord.Message, monotonic_ns: int) -> bool:
    """
    Informs a running script on whether it should kill itself from a timeout or kill commands
    """

    if message.id in killed_message_ids:
        killed_message_ids.remove(message.id)
        return True

    nanos = time.monotonic_ns() - monotonic_ns
    secs = nanos // 1000 // 1000 // 1000

    return secs > runtime_lim_secs


def old_discord_id(d_id: int) -> bool:
    """
    Returns true if the passed discord id was created more than a week ago
    """
    delta = (Time.now().as_datetime() - discord.utils.snowflake_time(d_id))
    return delta.days > 7


async def sonnet_sh(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    tstart: int = time.monotonic_ns()
    arguments: List[str] = message.content.split("\n")

    verbose = ctx.verbose
    cmds_dict = ctx.cmds_dict

    try:
        shellargs = shlex.split(arguments[0])
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        return 1

    self_name: str = ctx.command_name

    if verbose is False:
        await message.channel.send(f"ERROR: {self_name}: detected anomalous command execution")
        return 1

    if len(arguments[1:]) > 40:  # previously exec_lim, now custom
        await message.channel.send(f"ERROR: {self_name}: Exceeded limit of {40} commands to run")
        return 1

    # List of commands to execute and their args
    commandsparse: List[Tuple[str, List[str]]] = []

    # For over each command
    for hlindex, single_cmd in enumerate(arguments[1:]):

        # Split into arguments
        total: List[str] = single_cmd.split()

        # Check command exists and isint self
        if total[0] in cmds_dict and total[0] != self_name:

            # Get arglist separated from command
            argout: List[str] = total[1:]

            # For each shell arg, if the arg in the command is a shellarg macro then expand it
            # Do not use .replace, or arg1="${2} ${2}" arg2="${3} ${3}" can be used to exponentially build argument length
            # Only allow strict arg=${N} macro expansion
            for index, i in enumerate(shellargs):
                argout = [i if arg == ("${%d}" % index) else arg for arg in argout]

            # Add to command queue
            commandsparse.append((total[0], argout), )
        else:
            raise lib_sonnetcommands.CommandError(
                f"Could not parse command #{hlindex}\nScript commands have no prefix for cross compatibility\nAnd {self_name} is not runnable inside itself",
                private_message=f"`{total[0]}` is not a valid command"
                )

    # Keep reference to original message content
    keepref: str = message.content
    try:

        cache_args: List[str] = []

        newctx = pycopy.copy(ctx)
        newctx.verbose = False

        timeout = time.monotonic_ns()
        cancelled = False

        for totalcommand in commandsparse:

            if kill_this_task(message, timeout):
                cancelled = True
                break

            command = totalcommand[0]
            arguments = totalcommand[1]
            message.content = f'{ctx.conf_cache["prefix"]}{totalcommand[0]} ' + " ".join(totalcommand[1])

            if command in cmds_dict:

                cmd = SonnetCommand(cmds_dict[command], cmds_dict)

                permission = await parse_permissions(message, ctx.conf_cache, cmd['permission'])

                if permission:

                    try:
                        newctx.command_name = command
                        suc = (await cmd.execute_ctx(message, arguments, client, newctx)) or 0
                    except lib_sonnetcommands.CommandError as ce:
                        asyncio.create_task(ce.send(message))
                        suc = 1

                    # Stop processing if error
                    if suc != 0:
                        await message.channel.send(f"ERROR: {self_name}: command `{command}` exited with non success status")
                        return 1

                    # Regenerate cache
                    cache_args.append(cmd['cache'])
                else:
                    return 1

        ramfs: lexdpyk.ram_filesystem = ctx.ramfs

        for i in cache_args:
            cache_sweep(i, ramfs, message.guild)

        if cancelled:
            raise lib_sonnetcommands.CommandError(f"ERROR: Exceeded runtime limit of {runtime_lim_secs} seconds to execute commands or was killed by kill-script")

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if verbose: await message.channel.send(f"Completed execution of {len(commandsparse)} commands in {fmttime}ms")

    finally:
        message.content = keepref


class MapProcessError(Exception):
    __slots__ = ()


async def map_preprocessor_someexcept(message: discord.Message, args: List[str], client: discord.Client, cmds_dict: lexdpyk.cmd_modules_dict, conf_cache: Dict[str, Any],
                                      cname: str) -> Tuple[List[str], SonnetCommand, str, Tuple[List[str], List[str]]]:

    strargs = " ".join(args)

    # various slanted quotes, some are default for iOS keyboards (I think)
    slanted_quotes = ("\u201d", "\u201c", "\u2019", "\u2018")

    argset = set(strargs)
    has_weird_quotes = any(i in argset for i in slanted_quotes)

    try:
        targs: List[str] = shlex.split(strargs)
    except ValueError as ve:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): shlex parser could not parse args", private_message=f"ValueError: `{ve}`")

    if not targs:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): No command specified")

    # parses instances of -startargs and -endargs
    exargs: Tuple[List[str], List[str]] = ([], [])
    while targs and targs[0] in ['-s', '-e']:
        try:
            typ = targs.pop(0)
            if typ == '-s':
                exargs[0].extend(targs.pop(0).split())
            else:
                exargs[1].extend(targs.pop(0).split())
        except IndexError:
            raise lib_sonnetcommands.CommandError(f"ERROR({cname}): -s/-e specified but no input")

    if not targs:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): No command specified")

    command = targs.pop(0)

    if command not in cmds_dict:
        if has_weird_quotes:
            note = f"\n(you used slanted quotes in the args (`{'`, `'.join(slanted_quotes)}`), did you mean to use " \
                    "normal quotes (`'`, `\"`) instead?)\n(slanted quotes are not parsed by the argparser)"
        else:
            note = ""

        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): Command not found{note}", private_message=f"The command `{command}` does not exist")

    # get total length of -s and -e arguments multiplied by iteration count, projected memory use
    memory_size = sum(len(item) for arglist in exargs for item in arglist) * len(targs)

    # disallow really large expansions
    if memory_size >= 1 << 16:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): Total expansion size of arguments exceeds 64kb (projected at least {memory_size//1024} kbytes)")

    cmd = SonnetCommand(cmds_dict[command], cmds_dict)

    if not await parse_permissions(message, conf_cache, cmd.permission):
        raise MapProcessError("ERRNO")

    if cmd.execute_ctx == sonnet_map or cmd.execute_ctx == sonnet_async_map:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): Cannot call map/amap from {cname}")

    if len(targs) > exec_lim:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): Exceeded limit of {exec_lim} iterations")

    return targs, cmd, command, exargs


async def sonnet_map(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    tstart: int = time.monotonic_ns()
    cmds_dict = ctx.cmds_dict

    try:
        targs, cmd, command, exargs = await map_preprocessor_someexcept(message, args, client, cmds_dict, ctx.conf_cache, "map")
    except MapProcessError:
        return 1

    # Keep original message content
    keepref = message.content
    try:

        newctx = pycopy.copy(ctx)
        newctx.verbose = False
        newctx.command_name = command

        timeout = time.monotonic_ns()
        cancelled = False

        for i in targs:

            if kill_this_task(message, timeout):
                cancelled = True
                break

            arguments = exargs[0] + i.split() + exargs[1]

            message.content = f'{ctx.conf_cache["prefix"]}{command} {" ".join(arguments)}'

            try:
                suc = (await cmd.execute_ctx(message, arguments, client, newctx)) or 0
            except lib_sonnetcommands.CommandError as ce:
                asyncio.create_task(ce.send(message))
                suc = 1

            if suc != 0:
                raise lib_sonnetcommands.CommandError(f"ERROR(map): command `{command}` exited with non success status")

        # Do cache sweep on command
        cmd.sweep_cache(ctx.ramfs, message.guild)

        if cancelled:
            raise lib_sonnetcommands.CommandError(f"ERROR: Exceeded runtime limit of {runtime_lim_secs} seconds to execute commands or was killed by kill-script")

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs)} instances of {command} in {fmttime}ms")

    finally:
        message.content = keepref


async def wrapasyncerror(cmd: SonnetCommand, message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:
    try:
        await cmd.execute_ctx(message, args, client, ctx)
    except lib_sonnetcommands.CommandError as ce:  # catch CommandError to print message
        await ce.send(message)
    except asyncio.CancelledError:
        pass


async def sonnet_async_map(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    tstart: int = time.monotonic_ns()
    cmds_dict: lexdpyk.cmd_modules_dict = ctx.cmds_dict

    try:
        targs, cmd, command, exargs = await map_preprocessor_someexcept(message, args, client, cmds_dict, ctx.conf_cache, "amap")
    except MapProcessError:
        return 1

    promises = []

    newctx = pycopy.copy(ctx)
    newctx.verbose = False
    newctx.command_name = command

    timeout = time.monotonic_ns()

    for i in targs:

        arguments = exargs[0] + i.split() + exargs[1]

        # We need to copy the message object to avoid race conditions since all the commands run at once
        # All attrs are readonly except for content which we modify the pointer to, so avoiding a deepcopy is possible
        newmsg: discord.Message = pycopy.copy(message)
        newmsg.content = f'{ctx.conf_cache["prefix"]}{command} {" ".join(arguments)}'

        # Call error handler over command to allow catching CommandError in async
        promises.append(asyncio.create_task(wrapasyncerror(cmd, newmsg, arguments, client, newctx)))

    cancelled = False

    for idx in range(len(promises)):
        if kill_this_task(message, timeout):
            for p in promises[idx:]:
                p.cancel()
            cancelled = True
            break

        await promises[idx]

    # Do a cache sweep after running
    cmd.sweep_cache(ctx.ramfs, message.guild)

    if cancelled:
        raise lib_sonnetcommands.CommandError(f"ERROR: Exceeded runtime limit of {runtime_lim_secs} seconds to execute commands or was killed by kill-script")

    tend: int = time.monotonic_ns()

    fmttime: int = (tend - tstart) // 1000 // 1000

    if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs)} instances of {command} in {fmttime}ms")


async def sonnet_map_expansion(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    try:
        targs, _, command, exargs = await map_preprocessor_someexcept(message, args, client, ctx.cmds_dict, ctx.conf_cache, "map-expand")
    except MapProcessError:
        return 1

    out = io.StringIO()

    cheader = ctx.conf_cache["prefix"] + command

    for i in targs:

        arguments = exargs[0] + i.split() + exargs[1]

        out.write(f'{cheader} {" ".join(arguments)}\n')

    data = out.getvalue()

    if len(data) <= 2000:
        await message.channel.send(f"Expression expands to:\n```\n{data}```")

    else:
        fp = discord.File(io.BytesIO(data.encode("utf8")), filename="map-expand.txt")

        await message.channel.send("Expansion too large to preview, sent as file:", files=[fp])

    return 0


async def run_as_subcommand(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:

    # command check, perm check, run

    if args:
        command = args[0]

        if command not in ctx.cmds_dict:
            raise lib_sonnetcommands.CommandError("ERROR(sub): Command does not exist", private_message=f"Command `{command}` does not exist")

        sonnetc = SonnetCommand(ctx.cmds_dict[command], ctx.cmds_dict)

        if sonnetc.execute_ctx == run_as_subcommand:
            raise lib_sonnetcommands.CommandError("ERROR(sub): Cannot call sub from sub")

        if not await parse_permissions(message, ctx.conf_cache, sonnetc.permission):
            return 1

        # set to subcommand
        newctx = pycopy.copy(ctx)
        newctx.verbose = False
        newctx.command_name = command
        newmsg = pycopy.copy(message)
        newmsg.content = ctx.conf_cache["prefix"] + " ".join(args)

        return await sonnetc.execute_ctx(newmsg, args[1:], client, newctx)

    else:
        raise lib_sonnetcommands.CommandError("ERROR(sub): No command specified")


async def sleep_for(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:

    if ctx.verbose:
        raise lib_sonnetcommands.CommandError("ERROR(sleep): Can only run sleep as a subcommand")

    try:
        sleep_time = float(args[0])
    except IndexError:
        raise lib_sonnetcommands.CommandError("ERROR(sleep): No sleep time specified")
    except ValueError:
        raise lib_sonnetcommands.CommandError("ERROR(sleep): Could not parse sleep duration")

    if not (0 <= sleep_time <= 30):
        raise lib_sonnetcommands.CommandError("ERROR(sleep): Cannot sleep for more than 30 seconds or less than 0 seconds")

    await asyncio.sleep(sleep_time)


async def kill_task(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:

    kill_message, _ = await parse_channel_message_noexcept(message, args, client)

    killed_message_ids.add(kill_message.id)

    for i in list(killed_message_ids):
        if old_discord_id(i):
            killed_message_ids.remove(i)

    await message.channel.send(f"Added message with ID {kill_message.id} to task kill queue")


category_info = {'name': 'scripting', 'pretty_name': 'Scripting', 'description': 'Scripting tools for all your shell like needs'}

commands = {
    'sonnetsh':
        {
            'pretty_name': 'sonnetsh [args]\n<command1>\n...',
            'rich_description': 'To use [args] use syntax ${index}, 0 is commands own name',
            'description': 'Sonnet shell runtime, useful for automating setup',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': sonnet_sh
            },
    'map':
        {
            'pretty_name':
                'map [-s args] [-e args] <command> (<args>)+',
            'description':
                'Map a single command with multiple arguments',
            'rich_description':
                '''Use -e to append those args to the end of every run of the command, and -s to append args to the start of every command
For example `map -e "raiding and spam" ban <user> <user> <user>` would ban 3 users for raiding and spam''',
            'permission':
                'moderator',
            'cache':
                'keep',
            'execute':
                sonnet_map
            },
    'amap':
        {
            'pretty_name': 'amap [-s args] [-e args] <command> (<args>)+',
            'description': 'Like map, but processes asynchronously, meaning it ignores errors',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': sonnet_async_map
            },
    'map-expand':
        {
            'pretty_name': 'map-expand [-s args] [-e args] <command> (<args>)+',
            'description': 'Show what a map expression will expand to without actually running it',
            'permission': 'moderator',
            'execute': sonnet_map_expansion,
            },
    'sub': {
        'pretty_name': 'sub <command> [args]+',
        'description': 'runs a command as a subcommand',
        'execute': run_as_subcommand,
        },
    'sleep': {
        'pretty_name': 'sleep <seconds>',
        'description': 'Suspends execution for up to 30 seconds, for use in map/sonnetsh',
        'permission': 'moderator',
        'execute': sleep_for,
        },
    'kill-script':
        {
            'pretty_name': 'kill-script <message>',
            "description": "Kills a instance of sonnetsh/map/amap that came from the command sent by the indicated message",
            'permission': 'administrator',
            'execute': kill_task,
            }
    }

version_info: str = "2.0.2"
