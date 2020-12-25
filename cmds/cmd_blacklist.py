# Blacklist commands

import json

from lib_loaders import load_message_config
from lib_db_obfuscator import db_hlapi


async def update_csv_blacklist(message, args, name):

    if not(args) or len(args) != 1:
        await message.channel.send(f"Malformed {name}")
        raise RuntimeError(f"Malformed {name}")

    with db_hlapi(message.guild.id) as db:
        db.add_config(name, args[0])

    await message.channel.send(f"Updated {name} sucessfully")

async def wb_change(message, args, client, stats, cmds, ramfs):

    try:
        update_csv_blacklist(message, args, "word-blacklist")
    except RuntimeError:
        pass


async def word_in_word_change(message, args, client, stats, cmds, ramfs):

    try:
        update_csv_blacklist(message, args, "word-in-word-blacklist")
    except RuntimeError:
        pass


async def ftb_change(message, args, client, stats, cmds, ramfs):

    try:
        update_csv_blacklist(message, args, "filetype-blacklist")
    except RuntimeError:
        pass


async def regexblacklist_add(message, args, client, stats, cmds, ramfs):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config("regex-blacklist"))
        except json.decoder.JSONDecodeError:
            curlist = {"blacklist":[]}

        # Check if valid RegEx
        new_data = args[0]
        if new_data.startswith("/") and new_data.endswith("/g") and new_data.count(" ") == 0:
            curlist["blacklist"].append("__REGEXP "+new_data)
        else:
            await message.channel.send("ERROR: Malformed RegEx")
            return

        database.add_config("regex-blacklist", json.dumps(curlist))

    await message.channel.send("Sucessfully Updated RegEx")


async def regexblacklist_remove(message, args, client, stats, cmds, ramfs):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config("regex-blacklist"))
        except json.decoder.JSONDecodeError:
            await message.channel.send("ERROR: There is no RegEx")
            return

        # Check if in list
        remove_data = "__REGEXP "+args[0]
        if remove_data in curlist["blacklist"]:
            del curlist["blacklist"][curlist["blacklist"].index(remove_data)]
        else:
            await message.channel.send("ERROR: Pattern not found in RegEx")
            return

        # Update DB
        database.add_config("regex-blacklist", json.dumps(curlist))

    await message.channel.send("Sucessfully Updated RegEx")


async def list_blacklist(message, args, client, stats, cmds, ramfs):

    # Load temp ramfs to avoid passing as args
    mconf = load_message_config(message.guild.id, ramfs)

    # Format blacklist
    blacklist = {}
    blacklist["regex-blacklist"] = ["/"+i+"/g" for i in mconf["regex-blacklist"]]
    blacklist["word-blacklist"] = ",".join(mconf["word-blacklist"])
    blacklist["word-in-word-blacklist"] = ",".join(mconf["word-in-word-blacklist"])
    blacklist["filetype-blacklist"] = ",".join(mconf["filetype-blacklist"])

    # If word blacklist or filetype blacklist then load them
    for i in ["word-blacklist","filetype-blacklist", "word-in-word-blacklist"]:
        if blacklist[i]:
            blacklist[i] = [blacklist[i]]

    # If not existant then get rid of it
    for i in list(blacklist.keys()):
        if not blacklist[i]:
            del blacklist[i]

    # Format to str
    formatted = json.dumps(blacklist, indent=4).replace('\\\\','\\')

    # Print blacklist
    await message.channel.send(f"```\n{formatted}```")


async def set_blacklist_infraction_level(message, args, client, stats, cmds, ramfs):

    if args:
        action = args[0].lower()
    else:
        action = ""

    if not action in ["warn","kick","mute","ban"]:
        await message.channel.send("Blacklist action is not valid\nValid Actions: `warn` `mute` `kick` `ban`")
        return

    with db_hlapi(message.guild.id) as database:
        database.add_config("blacklist-action", action)

    await message.channel.send(f"Updated blacklist action to `{action}`")


async def change_rolewhitelist(message, args, client, stats, cmds, ramfs):

    if args:
        role = args[0].strip("<@&>")
    else:
        await message.channel.send("No role supplied")
        return

    try:
        role = int(role)
    except ValueError:
        await message.channel.send("Invalid role")
        return

    with db_hlapi(message.guild.id) as database:
        database.add_config("blacklist-whitelist", role)

    await message.channel.send(f"Updated role whitelist to {role}")


category_info = {
    'name': 'blacklist',
    'pretty_name': 'Blacklist',
    'description': 'Blacklist management commands.'
}


commands = {
    'wb-change': {
        'pretty_name': 'wb-change',
        'description': 'Change word blacklist for this guild.',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': wb_change
    },
    'add-regexblacklist': {
        'pretty_name': 'add-regexblacklist',
        'description': 'Add an item to regex blacklist.',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': regexblacklist_add
    },
    'wiwb-change': {
        'pretty_name': 'wiwb-change',
        'description': 'Change the WordInWord blacklist.',
        'permission':'administrator',
        'cache':'keep',
        'execute': word_in_word_change
    },
    'remove-regexblacklist': {
        'pretty_name': 'remove-regexblacklist',
        'description': 'Remove an item from regex blacklist.',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': regexblacklist_remove
    },
    'ftb-change': {
        'pretty_name': 'ftb-change',
        'description': 'Change filetype blacklist for this guild.',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': ftb_change
    },
    'list-blacklist': {
        'pretty_name': 'list-blacklist',
        'description': 'List all blacklists for this guild.',
        'permission':'administrator',
        'cache':'keep',
        'execute': list_blacklist
    },
    'blacklist-action': {
        'pretty_name': 'blacklist-action',
        'description': 'Set the action to occur when blacklist is broken',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': set_blacklist_infraction_level
    },
    'blacklist-whitelist': {
        'pretty_name': 'blacklist-whitelist',
        'description': 'Set a role that grants immunity from blacklisting',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': change_rolewhitelist
    }
    
}
