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
        return

    self_name = rawargs[0][len(kwargs["conf_cache"]["prefix"]):]

    commandsparse = []

    for single_cmd in arguments[1:]:
        total = single_cmd.split()
        if total[0] in kwargs["cmds_dict"] and total[0] != self_name:
            argout = total[1:]
            for index, i in enumerate(rawargs):
                argout = [arg.replace("${%d}" % index, i) for arg in argout]
            commandsparse.append([total[0], argout])
        else:
            await message.channel.send(f"{total[0]} is not a valid command\nScript commands have no prefix for cross compatability\nAnd {self_name} is not runnable inside itself")
            return

    cache_purge = False

    for totalcommand in commandsparse:

        command = totalcommand[0]
        arguments = totalcommand[1]

        if command in kwargs["cmds_dict"]:
            if "alias" in kwargs["cmds_dict"][command]:
                command = kwargs["cmds_dict"][command]["alias"]

            permission = await parse_permissions(message, kwargs["conf_cache"], kwargs["cmds_dict"][command]['permission'])

            if permission:

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

                # Regenerate cache
                if kwargs["cmds_dict"][command]['cache'] in ["purge", "regenerate"]:
                    cache_purge = True
            else:
                return

    if cache_purge:
        for i in ["caches", "regex"]:
            try:
                kwargs["ramfs"].rmdir(f"{message.guild.id}/{i}")
            except FileNotFoundError:
                pass


category_info = {'name': 'scripting', 'pretty_name': 'Scripting', 'description': 'Scripting tools for all your shell like needs'}

commands = {
    'sonnetsh':
        {
            'pretty_name': 'sonnetsh [args] \\n <command> <args>',
            'description': 'Sonnet shell runtime, useful for automating setup',
            'permission': 'everyone',
            'cache': 'keep',
            'execute': sonnet_sh
            },
    }

version_info = "1.1.6"
