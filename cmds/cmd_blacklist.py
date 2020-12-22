# Blacklist commands

import os, json

from lib_loaders import load_message_config
from lib_mdb_handler import db_handler
from lib_ramfs import ram_filesystem

async def wb_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    word_blacklist = "wsjg0operuyhg0834rjhg3408ghyu3goijwrgp9jgpoeij43p"


    if len(args) > 1:
        await message.channel.send("Malformed word blacklist.")
        return

    if len(args) == 1:
        word_blacklist = args[0]

    # Update word-blacklist in DB
    with db_handler() as db:
        db.add_to_table(f"{message.guild.id}_config", [
            ["property", "word-blacklist"],
            ["value", word_blacklist]
            ])
    await message.channel.send("Word blacklist updated successfully.")


async def word_in_word_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    word_blacklist = "wsjg0operuyhg0834rjhg3408ghyu3goijwrgp9jgpoeij43p"


    if len(args) > 1:
        await message.channel.send("Malformed word blacklist.")
        return

    if len(args) == 1:
        word_blacklist = args[0]

    # Update word-blacklist in DB
    with db_handler() as db:
        db.add_to_table(f"{message.guild.id}_config", [
            ["property", "word-in-word-blacklist"],
            ["value", word_blacklist]
            ])
    await message.channel.send("Word in word blacklist updated successfully.")


async def ftb_change(message, args, client, stats, cmds):

    if len(args) > 1:
        await message.channel.send("Malformed filetype blacklist.")
        return

    if len(args) == 1:
        filetype_blacklist = args[0]
    else:
        await message.channel.send("ERROR: No blacklist supplied")
        return

    # Update word-blacklist in DB
    with db_handler() as db:
        db.add_to_table(f"{message.guild.id}_config", [
            ["property", "filetype-blacklist"],
            ["value", filetype_blacklist]
            ])
    await message.channel.send("FileType blacklist updated successfully.")


async def regexblacklist_add(message, args, client, stats, cmds):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_handler() as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.fetch_rows_from_table(f"{message.guild.id}_config",["property","regex-blacklist"])[0][1])
        except (json.decoder.JSONDecodeError, IndexError):
            curlist = {"blacklist":[]}

        # Check if valid RegEx
        new_data = args[0]
        if new_data.startswith("/") and new_data.endswith("/g") and new_data.count(" ") == 0:
            curlist["blacklist"].append("__REGEXP "+new_data)
        else:
            await message.channel.send("ERROR: Malformed RegEx")
            return

        database.add_to_table(f"{message.guild.id}_config",[["property","regex-blacklist"],["value",json.dumps(curlist)]])

    await message.channel.send("Sucessfully Updated RegEx")


async def regexblacklist_remove(message, args, client, stats, cmds):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_handler() as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.fetch_rows_from_table(f"{message.guild.id}_config",["property","regex-blacklist"])[0][1])
        except (json.decoder.JSONDecodeError, IndexError):
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
        database.add_to_table(f"{message.guild.id}_config",[["property","regex-blacklist"],["value",json.dumps(curlist)]])

    await message.channel.send("Sucessfully Updated RegEx")


async def list_blacklist(message, args, client, stats, cmds):

    # Load temp ramfs to avoid passing as args
    tempramfs = ram_filesystem()
    mconf = load_message_config(message.guild.id, tempramfs)
    del tempramfs

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


async def set_blacklist_infraction_level(message, args, client, stats, cmds):

    if args:
        action = args[0].lower()
    else:
        action = ""

    if not action in ["warn","kick","mute","ban"]:
        await message.channel.send("Blacklist action is not valid")
        return

    with db_handler() as database:
        database.add_to_table(f"{message.guild.id}_config", [["property","blacklist-action"],["value", action]])

    await message.channel.send(f"Updated blacklist action to `{action}`")


async def change_rolewhitelist(message, args, client, stats, cmds):

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

    with db_handler() as database:
        database.add_to_table(f"{message.guild.id}_config",[["property","blacklist-whitelist"],["value",role]])

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
