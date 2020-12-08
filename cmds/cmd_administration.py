# Administration commands.
# bredo, 2020

import discord, os
from datetime import datetime
import json

from lib_mdb_handler import db_handler, db_error
from lib_load_blacklist import load_blacklist

async def recreate_db(message, args, client, stats, cmds):
    with db_handler() as db:
        db.make_new_table(f"{message.guild.id}_config",[["property", str, 1], ["value", str]])
        db.make_new_table(f"{message.guild.id}_infractions", [
        ["infractionID", str, 1],
        ["userID", str],
        ["moderatorID", str],
        ["type", str],
        ["reason", str],
        ["timestamp", int]
        ])
    await message.channel.send("done (unless something broke)")


async def wb_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    word_blacklist = "wsjg0operuyhg0834rjhg3408ghyu3goijwrgp9jgpoeij43p"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) > 1:
        await message.channel.send("Malformed word blacklist.")
        return

    if len(args) == 1:
        word_blacklist = args[0]

    # Update word-blacklist in DB
    try:
        with db_handler() as db:
            db.add_to_table(f"{message.guild.id}_config", [
                ["property", "word-blacklist"],
                ["value", word_blacklist]
                ])
        await message.channel.send("Word blacklist updated successfully.")
    except db_error.OperationalError:
        await message.channel.send("DB Error, run recreate-db")

    # Wipe cache
    os.remove(f"datastore/{message.guild.id}.cache.db")


async def ftb_change(message, args, client, stats, cmds):

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) > 1:
        await message.channel.send("Malformed filetype blacklist.")
        return

    if len(args) == 1:
        filetype_blacklist = args[0]
    else:
        await message.channel.send("ERROR: No blacklist supplied")
        return

    # Update word-blacklist in DB
    try:
        with db_handler() as db:
            db.add_to_table(f"{message.guild.id}_config", [
                ["property", "filetype-blacklist"],
                ["value", filetype_blacklist]
                ])
        await message.channel.send("FileType blacklist updated successfully.")
    except db_error.OperationalError:
        await message.channel.send("DB Error, run recreate-db")

    # Wipe cache
    os.remove(f"datastore/{message.guild.id}.cache.db")


async def inflog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    infraction_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) == 1:
        infraction_log = args[0]

    # Update infraction-log location in DB
    try:
        with db_handler() as db:
            db.add_to_table(f"{message.guild.id}_config", [
                ["property", "infraction-log"],
                ["value", infraction_log]
                ])
        await message.channel.send("Infraction log channel ID updated successfully.")
    except db_error.OperationalError:
        await message.channel.send("DB Error, run recreate-db")


async def joinlog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    join_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) == 1:
        join_log = args[0]

    # User is an admin and all arguments are correct. Send to database.
    try:
        with db_handler() as db:
            db.add_to_table(f"{message.guild.id}_config", [
                ["property", "join-log"],
                ["value", join_log]
                ])
        await message.channel.send("Join log channel ID updated successfully.")
    except db_error.OperationalError:
        await message.channel.send("DB Error, run recreate-db")


async def msglog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    message_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) == 1:
        message_log = args[0]

    # User is an admin and all arguments are correct. Send to database.
    try:
        with db_handler() as db:
            db.add_to_table(f"{message.guild.id}_config", [
                ["property", "message-log"],
                ["value", message_log]
                ])
        await message.channel.send("Message log channel ID updated successfully.")
    except db_error.OperationalError:
        await message.channel.send("DB Error, run recreate-db")


async def regexblacklist_add(message, args, client, stats, cmds):

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    db = db_handler()

    # Attempt to read blacklist if exists
    try:
        curlist = json.loads(db.fetch_rows_from_table(f"{message.guild.id}_config",["property","regex-blacklist"])[0][1])
    except db_error.OperationalError:
        curlist = {"blacklist":[]}
    except json.decoder.JSONDecodeError:
        curlist = {"blacklist":[]}
    except IndexError:
        curlist = {"blacklist":[]}


    # Check if valid RegEx
    new_data = args[0]
    if new_data.startswith("/") and new_data.endswith("/g") and new_data.count(" ") == 0:
        curlist["blacklist"].append("__REGEXP "+new_data)
    else:
        await message.channel.send("ERROR: Malformed RegEx")
        db.close()
        return

    try:
        db.add_to_table(f"{message.guild.id}_config",[["property","regex-blacklist"],["value",json.dumps(curlist)]])
    except db_error.OperationalError:
        await message.channel.send("ERROR: DB Error: run recreate-db")
        db.close()
        return

    # Wipe cache
    os.remove(f"datastore/{message.guild.id}.cache.db")

    # Close db
    db.close()

    await message.channel.send("Sucessfully Updated RegEx")


async def regexblacklist_remove(message, args, client, stats, cmds):

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    db = db_handler()

    # Attempt to read blacklist if exists
    try:
        curlist = json.loads(db.fetch_rows_from_table(f"{message.guild.id}_config",["property","regex-blacklist"])[0][1])
    except db_error.OperationalError:
        await message.channel.send("ERROR: There is no RegEx")
        db.close()
        return
    except json.decoder.JSONDecodeError:
        await message.channel.send("ERROR: There is no RegEx")
        db.close()
        return
    except IndexError:
        await message.channel.send("ERROR: There is no RegEx")
        db.close()
        return

    # Check if in list
    remove_data = "__REGEXP "+args[0]
    if remove_data in curlist["blacklist"]:
        del curlist["blacklist"][curlist["blacklist"].index(remove_data)]
    else:
        await message.channel.send("ERROR: Pattern not found in RegEx")
        db.close()
        return

    # Update DB
    try:
        db.add_to_table(f"{message.guild.id}_config",[["property","regex-blacklist"],["value",json.dumps(curlist)]])
    except db_error.OperationalError:
        await message.channel.send("ERROR: DB Error: run recreate-db")
        db.close()
        return

    # Wipe cache
    os.remove(f"datastore/{message.guild.id}.cache.db")

    # Close db
    db.close()

    await message.channel.send("Sucessfully Updated RegEx")


async def list_blacklist(message, args, client, stats, cmds):

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    # Format blacklist
    blacklist = load_blacklist(message.guild.id)
    blacklist["regex-blacklist"] = ["/"+i+"/g" for i in blacklist["regex-blacklist"]]
    blacklist["word-blacklist"] = ",".join(blacklist["word-blacklist"])
    blacklist["filetype-blacklist"] = ",".join(blacklist["filetype-blacklist"])
    
    # If word blacklist or filetype blacklist then load them
    for i in ["word-blacklist","filetype-blacklist"]:
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



category_info = {
    'name': 'administration',
    'pretty_name': 'Administration',
    'description': 'Administration commands.'
}


commands = {
    'recreate-db': {
        'pretty_name': 'recreate-db',
        'description': 'Recreate the database if it doesn\'t exist',
        'execute': recreate_db
    },
    'wb-change': {
        'pretty_name': 'wb-change',
        'description': 'Change word blacklist for this guild.',
        'execute': wb_change
    },
    'message-log': {
        'pretty_name': 'message-log',
        'description': 'Change message log for this guild.',
        'execute': msglog_change
    },
    'infraction-log': {
        'pretty_name': 'infraction-log',
        'description': 'Change infraction log for this guild.',
        'execute': inflog_change
    },
    'join-log': {
        'pretty_name': 'join-log',
        'description': 'Change join log for this guild.',
        'execute': joinlog_change
    },
    'add-regexblacklist': {
        'pretty_name': 'add-regexblacklist',
        'description': 'Add an item to regex blacklist.',
        'execute': regexblacklist_add
    },
    'remove-regexblacklist': {
        'pretty_name': 'remove-regexblacklist',
        'description': 'Remove an item from regex blacklist.',
        'execute': regexblacklist_remove
    },
    'ftb-change': {
        'pretty_name': 'ftb-change',
        'description': 'Change filetype blacklist for this guild.',
        'execute': ftb_change
    },
    'list-blacklist': {
        'pretty_name': 'list-blacklist',
        'description': 'List all blacklists for this guild.',
        'execute': list_blacklist
    },

}
