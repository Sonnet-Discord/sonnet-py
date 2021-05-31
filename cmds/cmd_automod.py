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
from lib_parsers import parse_role, parse_boolean

from typing import Any, Dict, List, Callable, Coroutine

re: Any = importlib.import_module(REGEX_VERSION)


class blacklist_input_error(Exception):
    pass


async def update_csv_blacklist(message: discord.Message, args: List[str], name: str, verbose: bool = True) -> None:

    if not (args) or len(args) != 1:
        await message.channel.send(f"Malformed {name}")
        raise blacklist_input_error(f"Malformed {name}")

    with db_hlapi(message.guild.id) as db:
        db.add_config(name, args[0])

    if verbose: await message.channel.send(f"Updated {name} successfully")


async def wb_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "word-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def word_in_word_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "word-in-word-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def ftb_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "filetype-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def add_regex_type(message: discord.Message, args: List[str], db_entry: str, verbose: bool = True) -> None:

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        raise blacklist_input_error("No regex")

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        if strjson := database.grab_config(db_entry):
            curlist = json.loads(strjson)
        else:
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

    if verbose: await message.channel.send("Successfully Updated RegEx")


async def remove_regex_type(message: discord.Message, args: List[str], db_entry: str, verbose: bool = True) -> None:

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        raise blacklist_input_error("No RegEx supplied")

    # Load DB
    with db_hlapi(message.guild.id) as database:

        # Attempt to read blacklist if exists
        if strjson := database.grab_config(db_entry):
            curlist = json.loads(strjson)
        else:
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

    if verbose: await message.channel.send("Successfully Updated RegEx")


async def regexblacklist_add(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await add_regex_type(message, args, "regex-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regexblacklist_remove(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await remove_regex_type(message, args, "regex-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regex_notifier_add(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await add_regex_type(message, args, "regex-notifier", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def regex_notifier_remove(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    try:
        await remove_regex_type(message, args, "regex-notifier", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def list_blacklist(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    mconf = kwargs["conf_cache"]

    # Format blacklist
    blacklist: Dict[str, Any] = {}
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


async def set_blacklist_infraction_level(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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


async def change_rolewhitelist(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    return await parse_role(message, args, "blacklist-whitelist", verbose=kwargs["verbose"])


async def antispam_set(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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
    outside_range = "ERROR: Cannot go outside range"
    if messages < 2 or messages > 64:
        await message.channel.send(f"{outside_range} 2-64 messages")
        return 1
    elif seconds > 10 or seconds < 0:
        await message.channel.send(f"{outside_range} 0-10 seconds")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("antispam", f"{int(messages)},{seconds}")

    if kwargs["verbose"]: await message.channel.send(f"Updated antispam timings to M:{int(messages)},S:{seconds}")


async def char_antispam_set(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    if not args:
        antispam = kwargs["conf_cache"]["char-antispam"]
        await message.channel.send(f"CharAntispam timings are M:{antispam[0]},S:{antispam[1]},C:{antispam[2]}")
        return

    if len(args) == 1:
        try:
            messages, seconds, chars = [float(i) for i in args[0].split(",")]
        except ValueError:
            await message.channel.send("ERROR: Incorrect args supplied")
            return 1

    elif len(args) > 1:
        try:
            messages = float(args[0])
            seconds = float(args[1])
            chars = float(args[2])
        except ValueError:
            await message.channel.send("ERROR: Incorrect args supplied")
            return 1

    # Prevent bullshit
    outside_range = "ERROR: Cannot go outside range"
    if messages < 2 or messages > 64:
        await message.channel.send(f"{outside_range} 2-64 messages")
        return 1
    elif seconds > 10 or seconds < 0:
        await message.channel.send(f"{outside_range} 0-10 seconds")
        return 1
    elif chars < 128 or chars > 2**16:
        await message.channel.send(f"{outside_range} 128-{2**16} chars")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("char-antispam", f"{int(messages)},{seconds},{int(chars)}")

    if kwargs["verbose"]: await message.channel.send(f"Updated char antispam timings to M:{int(messages)},S:{seconds},C:{int(chars)}")


async def antispam_time_set(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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
        return 0

    if mutetime < 0:
        await message.channel.send("ERROR: Mutetime cannot be negative")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("antispam-time", str(mutetime))

    if kwargs["verbose"]: await message.channel.send(f"Set antispam mute time to {mutetime} seconds")


class joinrules:
    def __init__(self, message: discord.Message):
        self.m = message

        self.ops: Dict[str, Tuple[Callable[[List[str]], Coroutine[Any, Any, None]], str]] = {
            "user": (self.useredit, "add|remove <id> 'Add or remove a userid from the watchlist'"),
            "timestamp": (self.timestampedit, "add|remove [offset(time[h|m|S])] 'Add or remove the account creation offset to warn for'"),
            "defaultpfp": (self.defaultpfpedit, "true|false 'Set whether or not to warn on a default pfp'"),
            "help": (self.printhelp, "'Print this help message'")
            }


    async def printhelp(self, args: List[str]) -> None:

        nsv: List[str] = [f"{i} {self.ops[i][1]}\n" for i in self.ops]
        await self.m.channel.send(f"JoinRule Help```py\n{''.join(nsv)}```")

    async def useredit(self, args: List[str]) -> None:
        # notifier-log-users
        await self.m.channel.send("NOT IMPLEMENTED (yet)")
        pass

    async def timestampedit(self, args: List[str]) -> None:
        # notifier-log-timestamp
        cnf_name: Final[str] = "notifier-log-timestamp"

        if args:
            if args[0] == "add" and len(args) >= 2:  # Add timestamp
                try:
                    if args[0][-1] in (multi := {"s": 1, "m": 60, "h": 3600}):
                        jointime = int(args[0][:-1]) * multi[args[0][-1]]
                    else:
                        jointime = int(args[0])
                except (ValueError, TypeError):
                    await message.channel.send("ERROR: Invalid time format")
                    return

                with db_hlapi(self.m.guild.id) as db:
                    db.add_config(cnf_name, str(jointime))

                await self.m.channel.send(f"Updated new user notify time to <{jointime} seconds since creation")

            elif args[0] == "remove":  # Remove timestamp
                with db_hlapi(self.m.guild.id) as db:
                    db.delete_config(cnf_name)
                await self.m.channel.send("Deleted new user notify time")

            else:  # Error
                await self.m.channel.send("Invalid args passed")

        else:  # Show current timestamp
            with db_hlapi(self.m.guild.id) as db:
                jointime = db.grab_config(cnf_name)
            await message.channel.send(f"new user notify is set to {jointime} seconds")

    async def defaultpfpedit(self, args: List[str]) -> None:
        # notifier-log-defaultpfp
        cnf_name: Final[str] = "notifier-log-defaultpfp"

        if args:
            with db_hlapi(self.m.guild.id) as db:
                db.add_config(cnf_name, str(true := int(parse_boolean(args[0]))))
            await self.m.channel.send(f"Updated defaultpfp checking to {bool(true)}")
        else:
            with db_hlapi(self.m.guild.id) as db:
                await self.m.channel.send(f"Defaultpfp checking is set to {bool(int(db.grab_config(cnf_name)))}")


async def add_joinrule(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    rules = joinrules(message)

    if args:

        if args[0] in rules.ops:
            await rules.ops[args[0]][0](args[1:])
        else:
            await message.channel.send("ERROR: Command not recognized")
            return 1

    else:
        await message.channel.send("No command specified, try help if you are stuck")
        return 1


category_info = {'name': 'automod', 'pretty_name': 'Automod', 'description': 'Automod management commands.'}

commands = {
    'set-joinrule': {
        'pretty_name': 'set-joinrule <type> <parameter>',
        'description': 'set joinrules to notify for',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': add_joinrule
        },
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
    'set-charantispam':
        {
            'pretty_name': 'set-charantispam <messages> <seconds> <chars>',
            'description': 'Set how many messages in seconds exeeding total chars to trigger antispam automute',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': char_antispam_set
            },
    'set-antispam':
        {
            'pretty_name': 'set-antispam <messages> <seconds>',
            'description': 'Set how many messages in seconds to trigger antispam automute',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': antispam_set
            },
    'mutetime-set': {
        'alias': 'set-mutetime'
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

version_info: str = "1.2.5-DEV"
