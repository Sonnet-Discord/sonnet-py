# Scripting engine to use sonnet commands
# Inspired by MantaroBots unix like commands
# And a lot of boredom :]
# Ultrabear 2021

import importlib

import shlex, discord, time, asyncio
import copy as pycopy

import lib_parsers

importlib.reload(lib_parsers)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)

from lib_parsers import parse_permissions
from lib_sonnetcommands import SonnetCommand, CommandCtx, cache_sweep

from typing import List, Any, Tuple, Awaitable, Dict
import lib_lexdpyk_h as lexdpyk

# This was placed after the exponential expansion exploit was found
# to help reduce severity if future exploits are found
#
# A limit of 1000 will reasonably never be reached by a normal user
exec_lim = 1000


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

    self_name: str = shellargs[0][len(ctx.conf_cache["prefix"]):]

    if verbose == False:
        await message.channel.send(f"ERROR: {self_name}: detected anomalous command execution")
        return 1

    if len(arguments[1:]) > exec_lim:
        await message.channel.send(f"ERROR: {self_name}: Exceeded limit of {exec_lim} commands to run")
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
            await message.channel.send(f"Could not parse command #{hlindex}\nScript commands have no prefix for cross compatibility\nAnd {self_name} is not runnable inside itself")
            return 1

    # Keep reference to original message content
    keepref: str = message.content
    try:

        cache_args: List[str] = []

        newctx = pycopy.copy(ctx)
        newctx.verbose = False

        for totalcommand in commandsparse:

            command = totalcommand[0]
            arguments = totalcommand[1]
            message.content = f'{ctx.conf_cache["prefix"]}{totalcommand[0]} ' + " ".join(totalcommand[1])

            if command in cmds_dict:

                cmd = SonnetCommand(cmds_dict[command], cmds_dict)

                permission = await parse_permissions(message, ctx.conf_cache, cmd['permission'])

                if permission:

                    try:
                        suc = (await cmd.execute_ctx(message, arguments, client, newctx)) or 0
                    except lib_sonnetcommands.CommandError as ce:
                        await message.channel.send(ce)
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

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if verbose: await message.channel.send(f"Completed execution of {len(commandsparse)} commands in {fmttime}ms")

    finally:
        message.content = keepref


class MapProcessError(Exception):
    __slots__ = ()


async def map_preprocessor_someexcept(message: discord.Message, args: List[str], client: discord.Client, cmds_dict: lexdpyk.cmd_modules_dict, conf_cache: Dict[str, Any],
                                      cname: str) -> Tuple[List[str], SonnetCommand, str, Tuple[List[str], List[str]]]:

    try:
        targs: List[str] = shlex.split(" ".join(args))
    except ValueError:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): shlex parser could not parse args")

    if not targs:
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): No command specified")

    # parses instances of -startargs and -endargs
    exargs: Tuple[List[str], List[str]] = ([], [])
    while targs[0] in ['-s', '-e']:
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
        raise lib_sonnetcommands.CommandError(f"ERROR({cname}): Command not found")

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

        for i in targs:

            arguments = exargs[0] + i.split() + exargs[1]

            message.content = f'{ctx.conf_cache["prefix"]}{command} {" ".join(arguments)}'

            try:
                suc = (await cmd.execute_ctx(message, arguments, client, newctx)) or 0
            except lib_sonnetcommands.CommandError as ce:
                await message.channel.send(ce)
                suc = 1

            if suc != 0:
                await message.channel.send(f"ERROR(map): command `{command}` exited with non success status")
                return 1

        # Do cache sweep on command
        cmd.sweep_cache(ctx.ramfs, message.guild)

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs)} instances of {command} in {fmttime}ms")

    finally:
        message.content = keepref


async def wrapasyncerror(cmd: SonnetCommand, message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:
    try:
        await cmd.execute_ctx(message, args, client, ctx)
    except lib_sonnetcommands.CommandError as ce:  # catch CommandError to print message
        try:
            await message.channel.send(ce)
        except discord.errors.Forbidden:
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

    promises: List[Awaitable[Any]] = []

    newctx = pycopy.copy(ctx)
    newctx.verbose = False

    for i in targs:

        arguments = exargs[0] + i.split() + exargs[1]

        # We need to copy the message object to avoid race conditions since all the commands run at once
        # All attrs are readonly except for content which we modify the pointer to, so avoiding a deepcopy is possible
        newmsg: discord.Message = pycopy.copy(message)
        newmsg.content = f'{ctx.conf_cache["prefix"]}{command} {" ".join(arguments)}'

        # Call error handler over command to allow catching CommandError in async
        promises.append(asyncio.create_task(wrapasyncerror(cmd, newmsg, arguments, client, newctx)))

    for p in promises:
        await p

    # Do a cache sweep after running
    cmd.sweep_cache(ctx.ramfs, message.guild)

    tend: int = time.monotonic_ns()

    fmttime: int = (tend - tstart) // 1000 // 1000

    if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs)} instances of {command} in {fmttime}ms")


async def run_as_subcommand(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:

    # command check, perm check, run

    if args:
        command = args[0]

        if command not in ctx.cmds_dict:
            raise lib_sonnetcommands.CommandError("ERROR(sub): Command does not exist")

        sonnetc = SonnetCommand(ctx.cmds_dict[command], ctx.cmds_dict)

        if sonnetc.execute_ctx == run_as_subcommand:
            raise lib_sonnetcommands.CommandError("ERROR(sub): Cannot call sub from sub")

        if not await parse_permissions(message, ctx.conf_cache, sonnetc.permission):
            return 1

        # set to subcommand
        newctx = pycopy.copy(ctx)
        newctx.verbose = False

        return await sonnetc.execute_ctx(message, args[1:], client, newctx)

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
    }

version_info: str = "1.2.13-DEV"
