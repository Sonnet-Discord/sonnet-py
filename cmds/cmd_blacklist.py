# Blacklist commands

import importlib

import json, io, discord, re2

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_loaders
importlib.reload(lib_loaders)

from lib_loaders import load_message_config
from lib_db_obfuscator import db_hlapi

re2.set_fallback_notification(re2.FALLBACK_EXCEPTION)


async def update_csv_blacklist(message, args, name):

    if not (args) or len(args) != 1:
        await message.channel.send(f"Malformed {name}")
        raise RuntimeError(f"Malformed {name}")

    with db_hlapi(message.guild.id) as db:
        db.add_config(name, args[0])

    await message.channel.send(f"Updated {name} sucessfully")


async def wb_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "word-blacklist")
    except RuntimeError:
        pass


async def word_in_word_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "word-in-word-blacklist")
    except RuntimeError:
        pass


async def ftb_change(message, args, client, **kwargs):

    try:
        await update_csv_blacklist(message, args, "filetype-blacklist")
    except RuntimeError:
        pass


async def regexblacklist_add(message, args, client, **kwargs):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config("regex-blacklist"))
        except (json.decoder.JSONDecodeError, TypeError):
            curlist = {"blacklist": []}

        # Check if valid RegEx
        new_data = args[0]
        if new_data.startswith("/") and new_data.endswith("/g") and new_data.count(" ") == 0:
            try:
                re2.findall(new_data[1:-2], message.content.encode("utf8"))
                curlist["blacklist"].append("__REGEXP " + new_data)
            except re2.error:
                await message.channel.send("ERROR: RegEx operations not supported in re2")
                return
        else:
            await message.channel.send("ERROR: Malformed RegEx")
            return

        database.add_config("regex-blacklist", json.dumps(curlist))

    await message.channel.send("Sucessfully Updated RegEx")


async def regexblacklist_remove(message, args, client, **kwargs):

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        return

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        try:
            curlist = json.loads(database.grab_config("regex-blacklist"))
        except (json.decoder.JSONDecodeError, TypeError):
            await message.channel.send("ERROR: There is no RegEx")
            return

        # Check if in list
        remove_data = "__REGEXP " + args[0]
        if remove_data in curlist["blacklist"]:
            del curlist["blacklist"][curlist["blacklist"].index(remove_data)]
        else:
            await message.channel.send("ERROR: Pattern not found in RegEx")
            return

        # Update DB
        database.add_config("regex-blacklist", json.dumps(curlist))

    await message.channel.send("Sucessfully Updated RegEx")


async def list_blacklist(message, args, client, **kwargs):

    # Load temp ramfs to avoid passing as args
    mconf = load_message_config(message.guild.id, kwargs["ramfs"])

    # Format blacklist
    blacklist = {}
    blacklist["regex-blacklist"] = ["/" + i + "/g" for i in mconf["regex-blacklist"]]
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
        action = ""

    if not action in ["warn", "kick", "mute", "ban"]:
        await message.channel.send("Blacklist action is not valid\nValid Actions: `warn` `mute` `kick` `ban`")
        return

    with db_hlapi(message.guild.id) as database:
        database.add_config("blacklist-action", action)

    await message.channel.send(f"Updated blacklist action to `{action}`")


async def change_rolewhitelist(message, args, client, **kwargs):

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


async def antispam_set(message, args, client, **kwargs):

    if not args:
        antispam = load_message_config(message.guild.id, kwargs["ramfs"])["antispam"]
        await message.channel.send(f"Antispam timings are {','.join(antispam)}")
        return

    if len(args) == 1:
        try:
            messages, seconds = [int(float(i)) for i in args[0].split(",")]
        except ValueError:
            await message.channel.send("Incorrect args supplied")
            return

    elif len(args) > 1:
        try:
            messages = int(float(args[0]))
            seconds = int(float(args[1]))
        except ValueError:
            await message.channel.send("Incorrect args supplied")
            return

    with db_hlapi(message.guild.id) as database:
        database.add_config("antispam", f"{messages},{seconds}")

    await message.channel.send(f"Updated antispam timings to M:{messages},S:{seconds}")


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
        'pretty_name': 'list-blacklist',
        'description': 'List all blacklists',
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
    'blacklist-whitelist':
        {
            'pretty_name': 'blacklist-whitelist <role>',
            'description': 'Set a role that grants immunity from blacklisting',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': change_rolewhitelist
            },
    'antispam-set':
        {
            'pretty_name': 'antispam-set <messages><,| ><seconds>',
            'description': 'Set how many messages in seconds to trigger antispam automute',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': antispam_set
            }
    }

version_info = "1.1.0-2"
