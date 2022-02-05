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
from lib_sonnetcommands import SonnetCommand, CommandCtx

from typing import List, Any, Tuple, Awaitable, Dict
import lib_lexdpyk_h as lexdpyk

# This was placed after the exponential expansion exploit was found
# to help reduce severity if future exploits are found
#
# A limit of 1000 will reasonably never be reached by a normal user
exec_lim = 1000


def do_cache_sweep(cache: str, ramfs: lexdpyk.ram_filesystem, guild: discord.Guild) -> None:

    if cache in ["purge", "regenerate"]:
        for i in ["caches", "regex"]:
            try:
                ramfs.rmdir(f"{guild.id}/{i}")
            except FileNotFoundError:
                pass

    elif cache.startswith("direct:"):
        for i in cache[len('direct:'):].split(";"):
            try:
                if i.startswith("(d)"):
                    ramfs.rmdir(f"{guild.id}/{i[3:]}")
                elif i.startswith("(f)"):
                    ramfs.remove_f(f"{guild.id}/{i[3:]}")
                else:
                    raise RuntimeError("Cache directive is invalid")
            except FileNotFoundError:
                pass


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
            do_cache_sweep(i, ramfs, message.guild)

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if verbose: await message.channel.send(f"Completed execution of {len(commandsparse)} commands in {fmttime}ms")

    finally:
        message.content = keepref


class MapProcessError(Exception):
    __slots__ = ()


async def map_preprocessor(message: discord.Message, args: List[str], client: discord.Client, cmds_dict: lexdpyk.cmd_modules_dict,
                           conf_cache: Dict[str, Any]) -> Tuple[List[str], int, SonnetCommand, str, List[str]]:

    try:
        targs: List[str] = shlex.split(" ".join(args))
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        raise MapProcessError("ERRNO")

    if targs:
        if targs[0] == "-e":
            if len(targs) >= 3:
                endlargs = targs[1].split()
                command = targs[2]
                targlen = 3
            else:
                await message.channel.send("No command specified/-e specified but no input")
                raise MapProcessError("ERRNO")
        else:
            endlargs = []
            command = targs[0]
            targlen = 1
    else:
        await message.channel.send("No command specified")
        raise MapProcessError("ERRNO")

    if command not in cmds_dict:
        await message.channel.send("Invalid command")
        raise MapProcessError("ERRNO")

    cmd = SonnetCommand(cmds_dict[command], cmds_dict)

    if not await parse_permissions(message, conf_cache, cmd.permission):
        raise MapProcessError("ERRNO")

    if len(targs[targlen:]) > exec_lim:
        await message.channel.send(f"ERROR: Exceeded limit of {exec_lim} iterations")
        raise MapProcessError("ERR LIM EXEEDED")

    return targs, targlen, cmd, command, endlargs


async def sonnet_map(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    tstart: int = time.monotonic_ns()
    cmds_dict = ctx.cmds_dict

    try:
        targs, targlen, cmd, command, endlargs = await map_preprocessor(message, args, client, cmds_dict, ctx.conf_cache)
    except MapProcessError:
        return 1

    # Keep original message content
    keepref = message.content
    try:

        newctx = pycopy.copy(ctx)
        newctx.verbose = False

        for i in targs[targlen:]:

            message.content = f'{ctx.conf_cache["prefix"]}{command} {i} {" ".join(endlargs)}'

            try:
                suc = (await cmd.execute_ctx(message, i.split() + endlargs, client, newctx)) or 0
            except lib_sonnetcommands.CommandError as ce:
                await message.channel.send(ce)
                suc = 1

            if suc != 0:
                await message.channel.send(f"ERROR: command `{command}` exited with non success status")
                return 1

        # Do cache sweep on command
        do_cache_sweep(cmd.cache, ctx.ramfs, message.guild)

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs[targlen:])} instances of {command} in {fmttime}ms")

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
        targs, targlen, cmd, command, endlargs = await map_preprocessor(message, args, client, cmds_dict, ctx.conf_cache)
    except MapProcessError:
        return 1

    promises: List[Awaitable[Any]] = []

    newctx = pycopy.copy(ctx)
    newctx.verbose = False

    for i in targs[targlen:]:

        # We need to copy the message object to avoid race conditions since all the commands run at once
        # All attrs are readonly except for content which we modify the pointer to, so avoiding a deepcopy is possible
        newmsg: discord.Message = pycopy.copy(message)
        newmsg.content = f'{ctx.conf_cache["prefix"]}{command} {i} {" ".join(endlargs)}'

        # Call error handler over command to allow catching CommandError in async
        promises.append(asyncio.create_task(wrapasyncerror(cmd, newmsg, i.split() + endlargs, client, newctx)))

    for p in promises:
        await p

    # Do a cache sweep after running
    do_cache_sweep(cmd['cache'], ctx.ramfs, message.guild)

    tend: int = time.monotonic_ns()

    fmttime: int = (tend - tstart) // 1000 // 1000

    if ctx.verbose: await message.channel.send(f"Completed execution of {len(targs[targlen:])} instances of {command} in {fmttime}ms")


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
                'map [-e args] <command> (<args>)+',
            'description':
                'Map a single command with multiple arguments',
            'rich_description':
                '''Use -e to append those args to the end of every run of the command
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
            'pretty_name': 'amap [-e args] <command> (<args>)+',
            'description': 'Like map, but processes asynchronously, meaning it ignores errors',
            'permission': 'moderator',
            'cache': 'keep',
            'execute': sonnet_async_map
            }
    }

version_info: str = "1.2.12-DEV"
