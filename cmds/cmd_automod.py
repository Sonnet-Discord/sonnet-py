# Blacklist commands

import importlib

import json, io, discord

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import sonnet_cfg

importlib.reload(sonnet_cfg)

from lib_db_obfuscator import db_hlapi
from sonnet_cfg import REGEX_VERSION
from lib_parsers import parse_role

re = importlib.import_module(REGEX_VERSION)


class blacklist_input_error(Exception):
    pass


async def update_csv_blacklist(message, args, name, verbose=True):

    if not (args) or len(args) != 1:
        await message.channel.send(f"Malformed {name}")
        raise blacklist_input_error(f"Malformed {name}")

    with db_hlapi(message.guild.id) as db:
        db.add_config(name, args[0])

    if verbose: await message.channel.send(f"Updated {name} sucessfully")


async def wb_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "word-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def word_in_word_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "word-in-word-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def ftb_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "filetype-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def add_regex_type(message, args, db_entry, verbose=True):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        raise blacklist_input_error("No regex")

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config(db_entry))
        except (json.decoder.JSONDecodeError, TypeError):
            curlist = {"blacklist": []}

        # Check if valid RegEx
        new_data = " ".join(args)
        if new_data.startswith("/") and new_data.endswith("/g"):
            try:
                re.findall(new_data[1:-2], message.content)
                curlist["blacklist"].append("__REGEXP " + new_data)
            except re.error:
                await message.channel.send("ERROR: RegEx operations not supported in re2")
                raise blacklist_input_error("Malformed regex")
        else:
            await message.channel.send("ERROR: Malformed RegEx")
            raise blacklist_input_error("Malformed regex")

        database.add_config(db_entry, json.dumps(curlist))

    if verbose: await message.channel.send("Sucessfully Updated RegEx")


async def remove_regex_type(message, args, db_entry, verbose=True):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        raise blacklist_input_error("No RegEx supplied")

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config(db_entry))
        except (json.decoder.JSONDecodeError, TypeError):
            await message.channel.send("ERROR: There is no RegEx")
            raise blacklist_input_error("No RegEx")

        # Check if in list
        remove_data = "__REGEXP " + " ".join(args)
        if remove_data in curlist["blacklist"]:
            del curlist["blacklist"][curlist["blacklist"].index(remove_data)]
        else:
            await message.channel.send("ERROR: Pattern not found in RegEx")
            raise blacklist_input_error("RegEx not found")

        # Update DB
        database.add_config(db_entry, json.dumps(curlist))

    if verbose: await message.channel.send("Sucessfully Updated RegEx")


async def regexblacklist_add(message, args, client, **kwargs):
    try:
        await add_regex_type(message, args, "regex-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regexblacklist_remove(message, args, client, **kwargs):
    try:
        await remove_regex_type(message, args, "regex-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regex_notifier_add(message, args, client, **kwargs):
    try:
        await add_regex_type(message, args, "regex-notifier", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regex_notifier_remove(message, args, client, **kwargs):
    try:
        await remove_regex_type(message, args, "regex-notifier", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def list_blacklist(message, args, client, **kwargs):

    mconf = kwargs["conf_cache"]

    # Format blacklist
    blacklist = {}
    blacklist["regex-blacklist"] = [f"/{i.pattern}/g" for i in mconf["regex-blacklist"]]
    blacklist["regex-notifier"] = [f"/{i.pattern}/g" for i in mconf["regex-notifier"]]
    blacklist["word-blacklist"] = ",".join(mconf["word-blacklist"])
    blacklist["word-in-word-blacklist"] = ",".join(mconf["word-in-word-blacklist"])
    blacklist["filetype-blacklist"] = ",".join(mconf["filetype-blacklist"])

    # If word blacklist or filetype blacklist then load them
    for i in ["word-blacklist", "filetype-blacklist", "word-in-word-blacklist"]:
        if blacklist[i]:
            blacklist[i] = [blacklist[i]]

    # If not existant then get rid of it
    for i in list(blacklist.keys()):
        if not blacklist[i]:
            del blacklist[i]

    # Format to str
    formatted = json.dumps(blacklist, indent=4)

    # Print blacklist
    formatted_pretty = "```json\n" + formatted.replace('\\\\', '\\') + "```"
    if len(formatted_pretty) <= 2000:
        await message.channel.send(formatted_pretty)
    else:
        file_to_upload = io.BytesIO()
        file_to_upload.write(formatted.encode("utf8"))
        file_to_upload.seek(0)
        fileobj = discord.File(file_to_upload, filename="blacklist.json")
        await message.channel.send("Total Blacklist too large to be previewed", file=fileobj)


async def set_blacklist_infraction_level(message, args, client, **kwargs):

    if args:
        action = args[0].lower()
    else:
        await message.channel.send(f"blacklist action is `{kwargs['conf_cache']['blacklist-action']}`")
        return

    if not action in ["warn", "kick", "mute", "ban"]:
        await message.channel.send("ERROR: Blacklist action is not valid\nValid Actions: `warn` `mute` `kick` `ban`")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("blacklist-action", action)

    if kwargs["verbose"]: await message.channel.send(f"Updated blacklist action to `{action}`")


async def change_rolewhitelist(message, args, client, **kwargs):

    return await parse_role(message, args, "blacklist-whitelist", verbose=kwargs["verbose"])


async def antispam_set(message, args, client, **kwargs):

    if not args:
        antispam = kwargs["conf_cache"]["antispam"]
        await message.channel.send(f"Antispam timings are M:{antispam[0]},S:{antispam[1]}")
        return

    if len(args) == 1:
        try:
            messages, seconds = [float(i) for i in args[0].split(",")]
        except ValueError:
            await message.channel.send("ERROR: Incorrect args supplied")
            return 1

    elif len(args) > 1:
        try:
            messages = float(args[0])
            seconds = float(args[1])
        except ValueError:
            await message.channel.send("ERROR: Incorrect args supplied")
            return 1

    # Prevent bullshit
    if messages < 2:
        await message.channel.send("ERROR: Cannot go below 2 messages")
        return 1
    elif seconds > 10:
        await message.channel.send("ERROR: Cannot go above 10 seconds")
        return 1
    elif seconds < 0:
        await message.channel.send("ERROR: Cannot go below 0 seconds")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("antispam", f"{int(messages)},{seconds}")

    if kwargs["verbose"]: await message.channel.send(f"Updated antispam timings to M:{int(messages)},S:{seconds}")


async def antispam_time_set(message, args, client, **kwargs):

    if args:
        try:
            if args[0][-1] in (multi := {"s": 1, "m": 60, "h": 3600}):
                mutetime = int(args[0][:-1]) * multi[args[0][-1]]
            else:
                mutetime = int(args[0])
        except (ValueError, TypeError):
            await message.channel.send("ERROR: Invalid time format")
            return 1
    else:
        mutetime = int(kwargs["conf_cache"]["antispam-time"])
        await message.channel.send(f"Antispam mute time is {mutetime} seconds")
        return

    if mutetime < 0:
        await message.channel.send("ERROR: Mutetime cannot be negative")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("antispam-time", str(mutetime))

    if kwargs["verbose"]: await message.channel.send(f"Set antispam mute time to {mutetime} seconds")


category_info = {'name': 'automod', 'pretty_name': 'Automod', 'description': 'Automod management commands.'}

commands = {
    'wb-change': {
        'pretty_name': 'wb-change <csv list>',
        'description': 'Change word blacklist',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': wb_change
        },
    'add-regexblacklist':
        {
            'pretty_name': 'add-regexblacklist <regex>',
            'description': 'Add an item to regex blacklist',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regexblacklist_add
            },
    'wiwb-change': {
        'pretty_name': 'wiwb-change <csv list>',
        'description': 'Change the WordInWord blacklist',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': word_in_word_change
        },
    'remove-regexblacklist':
        {
            'pretty_name': 'remove-regexblacklist <regex>',
            'description': 'Remove an item from regex blacklist',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regexblacklist_remove
            },
    'ftb-change': {
        'pretty_name': 'ftb-change <csv list>',
        'description': 'Change filetype blacklist',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': ftb_change
        },
    'list-blacklist': {
        'alias': 'list-automod'
        },
    'list-automod': {
        'pretty_name': 'list-automod',
        'description': 'List automod configs',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': list_blacklist
        },
    'blacklist-action':
        {
            'pretty_name': 'blacklist-action <warn|mute|kick|ban>',
            'description': 'Set the action to occur when blacklist is broken',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': set_blacklist_infraction_level
            },
    'blacklist-whitelist': {
        'alias': 'set-whitelist'
        },
    'whitelist-set': {
        'alias': 'set-whitelist'
        },
    'set-whitelist':
        {
            'pretty_name': 'set-whitelist <role>',
            'description': 'Set a role that grants immunity from blacklisting',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': change_rolewhitelist
            },
    'antispam-set': {
        'alias': 'set-antispam'
        },
    'set-antispam':
        {
            'pretty_name': 'set-antispam <messages> <seconds>',
            'description': 'Set how many messages in seconds to trigger antispam automute',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': antispam_set
            },
    'set-mutetime':
        {
            'pretty_name': 'set-mutetime <time[h|m|S]>',
            'description': 'Set how many seconds a person should be muted for with antispam automute',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': antispam_time_set
            },
    'add-regexnotifier':
        {
            'pretty_name': 'add-regexnotifier <regex>',
            'description': 'Add an item to regex notifier list',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regex_notifier_add
            },
    'remove-regexnotifier':
        {
            'pretty_name': 'remove-regexnotifier <regex>',
            'description': 'Remove an item from notifier list',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regex_notifier_remove
            },
    }

version_info = "1.2.2"
