# Scripting engine to use sonnet commands
# Inspired by MantaroBots unix like commands
# And alot of boredom :]
# Ultrabear 2021

import importlib

import shlex

import lib_parsers

importlib.reload(lib_parsers)

from lib_parsers import parse_permissions


async def sonnet_sh(message, args, client, **kwargs):

    arguments = message.content.split("\n")

    try:
        rawargs = shlex.split(arguments[0])
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        return 1

    self_name = rawargs[0][len(kwargs["conf_cache"]["prefix"]):]

    if kwargs["verbose"] == False:
        await message.channel.send(f"ERROR: {self_name}: detected anomalous command execution")
        return 1

    commandsparse = []

    for hlindex, single_cmd in enumerate(arguments[1:]):
        total = single_cmd.split()
        if total[0] in kwargs["cmds_dict"] and total[0] != self_name:
            argout = total[1:]
            for index, i in enumerate(rawargs):
                argout = [arg.replace("${%d}" % index, i) for arg in argout]
            commandsparse.append([total[0], argout])
        else:
            await message.channel.send(f"Could not parse command #{hlindex}\nScript commands have no prefix for cross compatability\nAnd {self_name} is not runnable inside itself")
            return 1

    cache_purge = False
    # Keep reference to original message content
    keepref = message.content

    for totalcommand in commandsparse:

        command = totalcommand[0]
        arguments = totalcommand[1]
        message.content = f'{kwargs["conf_cache"]["prefix"]}{totalcommand[0]} ' + " ".join(totalcommand[1])

        if command in kwargs["cmds_dict"]:
            if "alias" in kwargs["cmds_dict"][command]:
                command = kwargs["cmds_dict"][command]["alias"]

            permission = await parse_permissions(message, kwargs["conf_cache"], kwargs["cmds_dict"][command]['permission'])

            if permission:

                suc = (
                    await kwargs["cmds_dict"][command]['execute'](
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
                        cmds_dict=kwargs["cmds_dict"],
                        verbose=False,
                        )
                    ) or 0

                # Stop processing if error
                if suc != 0:
                    await message.channel.send(f"ERROR: {self_name}: command `{command}` exited with non sucess status")
                    message.content = keepref
                    return 1

                # Regenerate cache
                if kwargs["cmds_dict"][command]['cache'] in ["purge", "regenerate"]:
                    cache_purge = True
            else:
                # dont forget to re reference message content even if exec stops
                message.content = keepref
                return 1

    message.content = keepref

    if cache_purge:
        for i in ["caches", "regex"]:
            try:
                kwargs["ramfs"].rmdir(f"{message.guild.id}/{i}")
            except FileNotFoundError:
                pass


async def sonnet_map(message, args, client, **kwargs):

    try:
        targs = shlex.split(" ".join(args))
    except ValueError:
        await message.channel.send("ERROR: shlex parser could not parse args")
        return 1

    if targs:
        command = targs[0]
    else:
        await message.channel.send("No command specified")
        return 1

    if command not in kwargs["cmds_dict"]:
        await message.channel.send("Invalid command")
        return 1

    if "alias" in kwargs["cmds_dict"][command]:
        command = kwargs["cmds_dict"][command]["alias"]

    permission = await parse_permissions(message, kwargs["conf_cache"], kwargs["cmds_dict"][command]['permission'])
    if not permission:
        return 1

    keepref = message.content

    for i in targs[1:]:

        message.content = f'{kwargs["conf_cache"]["prefix"]}{command} {i}'

        suc = (
            await kwargs["cmds_dict"][command]['execute'](
                message,
                i.split(),
                client,
                stats=kwargs["stats"],
                cmds=kwargs["cmds"],
                ramfs=kwargs["ramfs"],
                bot_start=kwargs["bot_start"],
                dlibs=kwargs["dlibs"],
                main_version=kwargs["main_version"],
                kernel_ramfs=kwargs["kernel_ramfs"],
                conf_cache=kwargs["conf_cache"],
                cmds_dict=kwargs["cmds_dict"],
                verbose=False,
                )
            ) or 0

        if suc != 0:
            await message.channel.send(f"ERROR: command `{command}` exited with non sucess status")
            message.content = keepref
            return 1

    message.content = keepref

    if kwargs["cmds_dict"][command]['cache'] in ["purge", "regenerate"]:
        for i in ["caches", "regex"]:
            try:
                kwargs["ramfs"].rmdir(f"{message.guild.id}/{i}")
            except FileNotFoundError:
                pass


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
    'map': {
        'pretty_name': 'map <command> (<args>)+',
        'description': 'Map a single command with multiple arguments',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': sonnet_map
        },
    }

version_info = "1.2.2-DEV"
