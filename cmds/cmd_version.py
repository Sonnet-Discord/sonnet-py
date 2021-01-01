# Version printing tools
# Ultrabear 2020


from datetime import datetime


def prettyprint(inlist):
    maxln = 0
    minln = 0

    for i in inlist:
        if len(i[0]) > maxln:
            maxln = len(i[0])
        if len(i[1]) > minln:
            minln = len(i[1])

    outlist = []
    for i in inlist:
        outlist.append(f"{i[0]}{(maxln-len(i[0]))*' '} : {(minln-len(i[1]))*' '}{i[1]}")

    return outlist


async def print_version_info(message, args, client, **kwargs):

    bot_start_time = kwargs["bot_start"]
    dlib_version = kwargs["dlib_version"]
    main_version = kwargs["main_version"]
    modules = kwargs["cmds"]

    fmt = f"```\nKernel: {main_version}\nMessage Handlers: {dlib_version}\n\nModules:\n"

    for a in prettyprint([[i.category_info['pretty_name'], i.version_info] for i in modules]):
        fmt += f"  {a}\n"

    trunning = (datetime.utcnow() - datetime.utcfromtimestamp(bot_start_time))

    minutes = int((trunning.seconds-(seconds := trunning.seconds % 60)) / 60)
    hours = int((trunning.seconds - seconds - 60*minutes)/(60*60))

    fmt += f"\nBot Uptime: {trunning.days} Days, {hours}:{minutes}:{seconds}\n```"

    await message.channel.send(fmt)


async def uptime(message, args, client, **kwargs):

    bot_start_time = kwargs["bot_start"]

    trunning = (datetime.utcnow() - datetime.utcfromtimestamp(bot_start_time))

    minutes = int((trunning.seconds-(seconds := trunning.seconds % 60)) / 60)
    hours = int((trunning.seconds - seconds - 60*minutes)/(60*60))

    fmt = f"{trunning.days} Days, {hours}:{minutes}:{seconds}"

    await message.channel.send(fmt)


category_info = {
    'name': 'version',
    'pretty_name': 'Version',
    'description': 'Information about the current sonnet version'
}


commands = {
    'version-info': {
        'pretty_name': 'version-info',
        'description': 'Prints version info on sonnet modules',
        'permission':'everyone',
        'cache':'keep',
        'execute': print_version_info
    },
    'uptime': {
        'pretty_name': 'uptime',
        'description': 'Prints uptime',
        'permission':'everyone',
        'cache':'keep',
        'execute': uptime
    }

}


version_info = "1.0.2-DEV"
