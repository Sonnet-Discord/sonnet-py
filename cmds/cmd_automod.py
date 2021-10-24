# Blacklist commands

import importlib

import json, io, discord, string

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_constants

importlib.reload(lib_constants)
import lib_goparsers

importlib.reload(lib_goparsers)

from lib_goparsers import MustParseDuration
from lib_db_obfuscator import db_hlapi
from lib_sonnetconfig import REGEX_VERSION
from lib_parsers import parse_role, parse_boolean, parse_user_member

from typing import Any, Dict, List, Callable, Coroutine, Tuple, Optional
from typing import Final  # pytype: disable=import-error
import lib_constants as constants

re: Any = importlib.import_module(REGEX_VERSION)

wb_allowedrunes = string.ascii_lowercase + string.digits + ","
urlb_allowedrunes = string.ascii_lowercase + string.digits + "-,."


class blacklist_input_error(Exception):
    pass


async def update_csv_blacklist(message: discord.Message, args: List[str], name: str, verbose: bool = True, allowed: Optional[str] = None) -> None:
    if not message.guild:
        raise blacklist_input_error("No Guild Attached")

    if len(args) >= 2 and args[1] in ["rm", "remove"]:
        with db_hlapi(message.guild.id) as db:
            db.delete_config(name)

        await message.channel.send(f"Removed {name} config from database")
        return

    if not args or len(args) != 1:
        await message.channel.send(f"Malformed {name}")
        raise blacklist_input_error(f"Malformed {name}")

    if (allowed is not None) and not all(i in allowed for i in args[0]):
        await message.channel.send(f"The {name} does not support characters used, only supports {allowed}")
        raise blacklist_input_error("Unsupported chars")

    with db_hlapi(message.guild.id) as db:
        db.add_config(name, args[0])

    if verbose: await message.channel.send(f"Updated {name} successfully")


async def wb_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "word-blacklist", verbose=kwargs["verbose"], allowed=wb_allowedrunes)
    except blacklist_input_error:
        return 1


async def word_in_word_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "word-in-word-blacklist", verbose=kwargs["verbose"], allowed=wb_allowedrunes)
    except blacklist_input_error:
        return 1


async def ftb_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await update_csv_blacklist(message, args, "filetype-blacklist", verbose=kwargs["verbose"])
    except blacklist_input_error:
        return 1


async def urlblacklist_change(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    verbose: bool = kwargs["verbose"]

    try:
        await update_csv_blacklist(message, args, "url-blacklist", verbose=verbose, allowed=urlb_allowedrunes)
    except blacklist_input_error:
        return 1


async def add_regex_type(message: discord.Message, args: List[str], db_entry: str, verbose: bool = True) -> None:
    if not message.guild:
        raise blacklist_input_error("No Guild")

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
    if not message.guild:
        raise blacklist_input_error("No Guild")

    # Test if args supplied
    if not args:
        await message.channel.send("ERROR: no RegEx supplied")
        raise blacklist_input_error("No RegEx supplied")

    # Load DB
    with db_hlapi(message.guild.id) as db:

        # Attempt to read blacklist if exists
        if strjson := db.grab_config(db_entry):
            curlist = json.loads(strjson)
        else:
            await message.channel.send("ERROR: There is no RegEx")
            raise blacklist_input_error("No RegEx")

        # Remove by index
        if len(args) >= 2 and args[0] in ["-i", "--index"]:
            try:
                del curlist["blacklist"][int(args[1])]
            except ValueError:
                await message.channel.send("ERROR: Index specified but invalid int")
                raise blacklist_input_error("Pattern not in regex")
            except IndexError:
                await message.channel.send("ERROR: Pattern not found in RegEx index")
                raise blacklist_input_error("Pattern not in regex")

        # Remove by value
        else:
            # Check if in list
            remove_data = f"__REGEXP {' '.join(args)}"
            if remove_data in curlist["blacklist"]:
                del curlist["blacklist"][curlist["blacklist"].index(remove_data)]
            else:
                await message.channel.send("ERROR: Pattern not found in RegEx")
                raise blacklist_input_error("RegEx not found")

        # Update DB
        db.add_config(db_entry, json.dumps(curlist))

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

    mconf: Dict[str, Any] = kwargs["conf_cache"]

    raw = False
    if args and args[0] in ["--raw", "-r"]:
        raw = True

    # Format blacklist
    blacklist: Dict[str, Any] = {}
    blacklist["regex-blacklist"] = [f"/{i.pattern}/g" for i in mconf["regex-blacklist"]]
    blacklist["regex-notifier"] = [f"/{i.pattern}/g" for i in mconf["regex-notifier"]]
    blacklist["word-blacklist"] = ",".join(mconf["word-blacklist"])
    blacklist["word-in-word-blacklist"] = ",".join(mconf["word-in-word-blacklist"])
    blacklist["filetype-blacklist"] = ",".join(mconf["filetype-blacklist"])
    blacklist["url-blacklist"] = ",".join(mconf["url-blacklist"])

    # If word blacklist or filetype blacklist then load them
    for i in ["word-blacklist", "filetype-blacklist", "word-in-word-blacklist", "url-blacklist"]:
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
    if len(formatted_pretty) <= 2000 and not raw:
        await message.channel.send(formatted_pretty)
    else:
        # Error message is first one if raw is False, second one if raw is True
        errmsg = ["Total Blacklist too large to be previewed", "--raw specified, file supplied"][raw]
        file_to_upload = io.BytesIO()
        file_to_upload.write(formatted.encode("utf8"))
        file_to_upload.seek(0)
        fileobj = discord.File(file_to_upload, filename="blacklist.json")
        await message.channel.send(errmsg, file=fileobj)


async def set_blacklist_infraction_level(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

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
    if not message.guild:
        return 1

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
    if not (2 <= messages <= 64):
        await message.channel.send(f"{outside_range} 2-64 messages")
        return 1
    elif not (0 <= seconds <= 10):
        await message.channel.send(f"{outside_range} 0-10 seconds")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("antispam", f"{int(messages)},{seconds}")

    if kwargs["verbose"]: await message.channel.send(f"Updated antispam timings to M:{int(messages)},S:{seconds}")


async def char_antispam_set(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

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
    if not (2 <= messages <= 64):
        await message.channel.send(f"{outside_range} 2-64 messages")
        return 1
    elif not (0 <= seconds <= 10):
        await message.channel.send(f"{outside_range} 0-10 seconds")
        return 1
    elif not (128 <= chars <= 2**16):
        await message.channel.send(f"{outside_range} 128-{2**16} chars")
        return 1

    with db_hlapi(message.guild.id) as database:
        database.add_config("char-antispam", f"{int(messages)},{seconds},{int(chars)}")

    if kwargs["verbose"]: await message.channel.send(f"Updated char antispam timings to M:{int(messages)},S:{seconds},C:{int(chars)}")


async def antispam_time_set(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    if args:
        try:
            mutetime = MustParseDuration(args[0])
        except lib_goparsers.errors.ParseFailureError:
            await message.channel.send("ERROR: Invalid time format")
            return 1
    else:
        mutetime = int(kwargs["conf_cache"]["antispam-time"])
        await message.channel.send(f"Antispam mute time is {mutetime} seconds")
        return 0

    if mutetime < 0:
        await message.channel.send("ERROR: Mutetime cannot be negative")
        return 1

    elif mutetime >= 60 * 60 * 256:
        await message.channel.send("ERROR: Mutetime cannot be greater than 256 hours")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("antispam-time", str(mutetime))

    if kwargs["verbose"]: await message.channel.send(f"Set antispam mute time to {mutetime} seconds")


class NoGuildError(Exception):
    pass


class joinrules:
    __slots__ = "m", "guild", "ops"

    def __init__(self, message: discord.Message):
        if not message.guild:
            raise NoGuildError(f"{message}: contains no guild")

        self.m: Final[discord.Message] = message
        self.guild = message.guild

        self.ops: Dict[str, Tuple[Callable[[List[str], discord.Client], Coroutine[Any, Any, int]], str]] = {  # pytype: disable=annotation-type-mismatch
            "user": (self.useredit, "add|remove <id> 'Add or remove a userid from the watchlist'"),
            "timestamp": (self.timestampedit, "add|remove [offset(time[h|m|S])] 'Add or remove the account creation offset to warn for'"),
            "defaultpfp": (self.defaultpfpedit, "true|false 'Set whether or not to notify on a default pfp'"),
            "help": (self.printhelp, "'Print this help message'")
            }

    async def printhelp(self, args: List[str], client: discord.Client) -> int:

        nsv: List[str] = [f"{i} {self.ops[i][1]}\n" for i in self.ops]
        await self.m.channel.send(f"JoinRule Help```py\n{''.join(nsv)}```")

        return 0

    async def useredit(self, args: List[str], client: discord.Client) -> int:
        # notifier-log-users
        cnf_name: Final[str] = "notifier-log-users"

        if len(args) >= 2:
            if args[0] == "add":
                try:
                    user, _ = await parse_user_member(self.m, args, client, argindex=1)
                except lib_parsers.errors.user_parse_error:
                    return 1

                with db_hlapi(self.guild.id) as db:
                    blusers: List[int] = json.loads(db.grab_config(cnf_name) or "[]")

                if user.id in blusers:
                    await self.m.channel.send("ERROR: This user is already in the notifier")
                    return 1

                blusers.append(user.id)

                with db_hlapi(self.guild.id) as db:
                    db.add_config(cnf_name, json.dumps(blusers))

                await self.m.channel.send(f"Added {user.mention} with ID {user.id} joining to the notifier log", allowed_mentions=discord.AllowedMentions.none())

            elif args[0] == "remove":
                try:
                    user, _ = await parse_user_member(self.m, args, client, argindex=1)
                except lib_parsers.errors.user_parse_error:
                    return 1

                with db_hlapi(self.guild.id) as db:
                    blusers = json.loads(db.grab_config(cnf_name) or "[]")

                if user.id not in blusers:
                    await self.m.channel.send("ERROR: This user is not in the notifier")
                    return 1

                del blusers[blusers.index(user.id)]

                with db_hlapi(self.guild.id) as db:
                    db.add_config(cnf_name, json.dumps(blusers))

                await self.m.channel.send(f"Removed {user.mention} with ID {user.id} joining from the notifier log", allowed_mentions=discord.AllowedMentions.none())

        else:
            await self.m.channel.send(constants.sonnet.error_args.not_enough)
            return 1

        return 0

    async def timestampedit(self, args: List[str], client: discord.Client) -> int:
        # notifier-log-timestamp
        cnf_name: Final[str] = "notifier-log-timestamp"

        if args:  # I hate this code holy shit its so unreadable
            if args[0] == "add" and len(args) >= 2:  # Add timestamp

                try:  # Parse time
                    jointime = MustParseDuration(args[1])
                except lib_goparsers.errors.ParseFailureError:
                    await self.m.channel.send("ERROR: Invalid time format")
                    return 1

                if jointime < 0 or jointime > 60 * 60 * 24 * 30:  # Only allow JT up to a month, ive learned to never trust input the hard way
                    await self.m.channel.send("ERROR: Time range entered is larger than one month (~30 days)")
                    return 1

                with db_hlapi(self.guild.id) as db:  # Add to db
                    db.add_config(cnf_name, str(jointime))

                await self.m.channel.send(f"Updated new user notify time to <{jointime} seconds since creation")
                return 0

            elif args[0] == "remove":  # Remove timestamp

                with db_hlapi(self.guild.id) as db:
                    db.delete_config(cnf_name)
                await self.m.channel.send("Deleted new user notify time")
                return 0

            else:  # Error
                await self.m.channel.send("Invalid args passed")
                return 1

        else:  # Show current timestamp

            with db_hlapi(self.guild.id) as db:
                jointime_str = db.grab_config(cnf_name)
            await self.m.channel.send(f"new user notify is set to {jointime_str} seconds")
            return 0

    async def defaultpfpedit(self, args: List[str], client: discord.Client) -> int:
        # notifier-log-defaultpfp
        cnf_name: Final[str] = "notifier-log-defaultpfp"

        if args:
            with db_hlapi(self.guild.id) as db:
                db.add_config(cnf_name, str(true := int(parse_boolean(args[0]))))
            await self.m.channel.send(f"Updated defaultpfp checking to {bool(true)}")
        else:
            with db_hlapi(self.guild.id) as db:
                await self.m.channel.send(f"Defaultpfp checking is set to {bool(int(db.grab_config(cnf_name) or 0))}")

        return 0


async def add_joinrule(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        rules = joinrules(message)
    except NoGuildError:
        return 1

    if args:

        if args[0] in rules.ops:
            return await rules.ops[args[0]][0](args[1:], client)
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
    'wb-change':
        {
            'pretty_name': 'wb-change <csv list> [rm|remove]',
            'description': 'Change word blacklist, use `wb-change - rm` to reset',
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
    'wiwb-change':
        {
            'pretty_name': 'wiwb-change <csv list> [rm|remove]',
            'description': 'Change the WordInWord blacklist, use `wiwb-change - rm` to reset',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': word_in_word_change
            },
    'remove-regexblacklist':
        {
            'pretty_name': 'remove-regexblacklist <<regex> | -i INDEX> ',
            'description': 'Remove an item from regex blacklist',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regexblacklist_remove
            },
    'ftb-change':
        {
            'pretty_name': 'ftb-change <csv list> [rm|remove]',
            'description': 'Change filetype blacklist, use `ftb-change - rm` to reset',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': ftb_change
            },
    'urlb-change':
        {
            'pretty_name': 'urlb-change <csv list> [rm|remove]',
            'description': 'Change url blacklist, use `urlb-change - rm` to reset',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': urlblacklist_change
            },
    'list-blacklist': {
        'alias': 'list-automod'
        },
    'list-automod':
        {
            'pretty_name': 'list-automod [-r | --raw]',
            'description': 'List automod configs, use --raw to forcedump json file',
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
            'pretty_name': 'remove-regexnotifier <<regex> | -i INDEX>',
            'description': 'Remove an item from notifier list',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': regex_notifier_remove
            },
    }

version_info: str = "1.2.9-DEV"
