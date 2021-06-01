# Scripting engine to use sonnet commands
# Inspired by MantaroBots unix like commands
# And a lot of boredom :]
# Ultrabear 2021

import importlib

import shlex, discord, time

import lib_parsers

importlib.reload(lib_parsers)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)

from lib_parsers import parse_permissions

from typing import List, Any, Tuple
import lib_lexdpyk_h as lexdpyk


async def sonnet_sh(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    tstart: int = time.monotonic_ns()
    arguments: List[str] = message.content.split("\n")

    verbose: bool = kwargs["verbose"]
    cmds_dict: lexdpyk.cmd_modules_dict = kwargs["cmds_dict"]

    try:
        rawargs = shlex.split(arguments[0])
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        return 1

    self_name: str = rawargs[0][len(kwargs["conf_cache"]["prefix"]):]

    if verbose == False:
        await message.channel.send(f"ERROR: {self_name}: detected anomalous command execution")
        return 1

    commandsparse: List[Tuple[str, List[str]]] = []

    for hlindex, single_cmd in enumerate(arguments[1:]):
        total: List[str] = single_cmd.split()
        if total[0] in cmds_dict and total[0] != self_name:
            argout: List[str] = total[1:]
            for index, i in enumerate(rawargs):
                argout = [arg.replace("${%d}" % index, i) for arg in argout]
            commandsparse.append((total[0], argout), )
        else:
            await message.channel.send(f"Could not parse command #{hlindex}\nScript commands have no prefix for cross compatability\nAnd {self_name} is not runnable inside itself")
            return 1

    # Keep reference to original message content
    keepref: str = message.content
    try:

        cache_purge: bool = False
        cache_directives: List[str] = []

        for totalcommand in commandsparse:

            command = totalcommand[0]
            arguments = totalcommand[1]
            message.content = f'{kwargs["conf_cache"]["prefix"]}{totalcommand[0]} ' + " ".join(totalcommand[1])

            if command in cmds_dict:
                if "alias" in cmds_dict[command]:
                    command = cmds_dict[command]["alias"]

                permission = await parse_permissions(message, kwargs["conf_cache"], cmds_dict[command]['permission'])

                if permission:

                    suc = (
                        await cmds_dict[command]['execute'](
                            message,
                            arguments,
                            client,
                            stats=kwargs["stats"],
                            cmds=kwargs["cmds"],
                            ramfs=kwargs["ramfs"],
                            bot_start=kwargs["bot_start"],
                            dlibs=kwargs["dlibs"],
                            main_version=kwargs["main_version"],
                            kernel_ramfs=kwargs["kernel_ramfs"],
                            conf_cache=kwargs["conf_cache"],
                            cmds_dict=cmds_dict,
                            verbose=False,
                            )
                        ) or 0

                    # Stop processing if error
                    if suc != 0:
                        await message.channel.send(f"ERROR: {self_name}: command `{command}` exited with non success status")
                        return 1

                    # Regenerate cache
                    if cmds_dict[command]['cache'] in ["purge", "regenerate"]:
                        cache_purge = True
                    elif cmds_dict[command]['cache'].startswith("direct:"):
                        cache_directives.extend(cmds_dict[command]['cache'][len('direct:'):].split(";"))
                else:
                    return 1

        ramfs: lexdpyk.ram_filesystem = kwargs["ramfs"]

        if cache_purge:
            for i in ["caches", "regex"]:
                try:
                    ramfs.rmdir(f"{message.guild.id}/{i}")
                except FileNotFoundError:
                    pass

        for i in cache_directives:
            try:
                if i.startswith("(d)"):
                    ramfs.rmdir(f"{message.guild.id}/{i[3:]}")
                elif i.startswith("(f)"):
                    ramfs.remove_f(f"{message.guild.id}/{i[3:]}")
                else:
                    raise RuntimeError("Cache directive is invalid")
            except FileNotFoundError:
                pass

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if verbose: await message.channel.send(f"Completed execution of {len(commandsparse)} commands in {fmttime}ms")

    finally:
        message.content = keepref


async def sonnet_map(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    tstart: int = time.monotonic_ns()
    cmds_dict: lexdpyk.cmd_modules_dict = kwargs["cmds_dict"]

    try:
        targs: List[str] = shlex.split(" ".join(args))
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        return 1

    if targs:
        if targs[0] == "-e":
            if len(targs) >= 3:
                endlargs = targs[1].split()
                command = targs[2]
                targlen = 3
            else:
                await message.channel.send("No command specified/-e specified but no input")
                return 1
        else:
            endlargs = []
            command = targs[0]
            targlen = 1
    else:
        await message.channel.send("No command specified")
        return 1

    if command not in cmds_dict:
        await message.channel.send("Invalid command")
        return 1

    if "alias" in cmds_dict[command]:
        command = cmds_dict[command]["alias"]

    if not await parse_permissions(message, kwargs["conf_cache"], cmds_dict[command]['permission']):
        return 1

    # Keep original message content
    keepref = message.content
    try:

        for i in targs[targlen:]:

            message.content = f'{kwargs["conf_cache"]["prefix"]}{command} {i} {" ".join(endlargs)}'

            suc = (
                await cmds_dict[command]['execute'](
                    message,
                    i.split() + endlargs,
                    client,
                    stats=kwargs["stats"],
                    cmds=kwargs["cmds"],
                    ramfs=kwargs["ramfs"],
                    bot_start=kwargs["bot_start"],
                    dlibs=kwargs["dlibs"],
                    main_version=kwargs["main_version"],
                    kernel_ramfs=kwargs["kernel_ramfs"],
                    conf_cache=kwargs["conf_cache"],
                    cmds_dict=cmds_dict,
                    verbose=False,
                    )
                ) or 0

            if suc != 0:
                await message.channel.send(f"ERROR: command `{command}` exited with non success status")
                return 1


        if cmds_dict[command]['cache'] in ["purge", "regenerate"]:
            for i in ["caches", "regex"]:
                try:
                    kwargs["ramfs"].rmdir(f"{message.guild.id}/{i}")
                except FileNotFoundError:
                    pass

        elif cmds_dict[command]['cache'].startswith("direct:"):
            for i in cmds_dict[command]['cache'][len('direct:'):].split(";"):
                try:
                    if i.startswith("(d)"):
                        ramfs.rmdir(f"{message.guild.id}/{i[3:]}")
                    elif i.startswith("(f)"):
                        ramfs.remove_f(f"{message.guild.id}/{i[3:]}")
                    else:
                        raise RuntimeError("Cache directive is invalid")
                except FileNotFoundError:
                    pass

        tend: int = time.monotonic_ns()

        fmttime: int = (tend - tstart) // 1000 // 1000

        if kwargs["verbose"]: await message.channel.send(f"Completed execution of {len(targs[targlen:])} instances of {command} in {fmttime}ms")

    finally:
        message.content = keepref


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
    }

version_info: str = "1.2.6-DEV"
