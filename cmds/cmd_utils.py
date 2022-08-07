# Utility Commands
# Funey, 2020

import asyncio
import importlib
import io
import random
import time
from datetime import datetime

import discord
import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)
import lib_constants

importlib.reload(lib_constants)
import lib_lexdpyk_h

importlib.reload(lib_lexdpyk_h)
import lib_compatibility

importlib.reload(lib_compatibility)
import lib_sonnetcommands

importlib.reload(lib_sonnetcommands)
import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_tparse

importlib.reload(lib_tparse)
import lib_datetimeplus

importlib.reload(lib_datetimeplus)

from typing import Any, Final, List, Optional, Tuple, Dict, cast

import lib_constants as constants
import lib_lexdpyk_h as lexdpyk
from lib_compatibility import discord_datetime_now, user_avatar_url
from lib_db_obfuscator import db_hlapi
from lib_loaders import embed_colors, load_embed_color
from lib_parsers import (parse_boolean, parse_permissions, parse_core_permissions, parse_user_member_noexcept, parse_channel_message_noexcept, generate_reply_field, grab_files)
from lib_sonnetcommands import CallCtx, CommandCtx, SonnetCommand
from lib_sonnetconfig import BOT_NAME
from lib_tparse import Parser
from lib_datetimeplus import Time


def add_timestamp(embed: discord.Embed, name: str, start: int, end: int) -> None:
    embed.add_field(name=name, value=f"{(end - start) / 100}ms", inline=False)


def ctime(t: float) -> int:
    return round(t * 100000)


async def ping_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    stats = kwargs["stats"]

    ping_embed = discord.Embed(title="Pong!", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))

    add_timestamp(ping_embed, "Total Process Time", stats["start"], stats["end"])
    add_timestamp(ping_embed, "Config Load Time", stats["start-load-blacklist"], stats["end-load-blacklist"])
    add_timestamp(ping_embed, "Automod Process Time", stats["start-automod"], stats["end-automod"])
    add_timestamp(ping_embed, "WS Latency", 0, ctime(client.latency))

    send_start = ctime(time.time())
    sent_message = await message.channel.send(embed=ping_embed)
    send_end = ctime(time.time())

    add_timestamp(ping_embed, "Send Message", send_start, send_end)

    await sent_message.edit(embed=ping_embed)


# Must use datetime due to discord.py being naive
def parsedate(indata: Optional[datetime]) -> str:
    if indata is not None:
        basetime = format(indata, '%a, %d %b %Y %H:%M:%S')
        days = (discord_datetime_now() - indata).days
        return f"{basetime} ({days} day{'s' * (days != 1)} ago)"
    else:
        return "ERROR: Could not fetch this date"


def _get_highest_perm(message: discord.Message, member: discord.Member, conf_cache: Dict[str, Any]) -> str:
    if not isinstance(message.channel, discord.TextChannel):
        return "everyone"

    highest = "everyone"
    for i in ["moderator", "administrator", "owner"]:
        if parse_core_permissions(message.channel, member, conf_cache, i):
            highest = i
        else:
            break

    return highest


async def profile_function(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    user, member = await parse_user_member_noexcept(message, args, client, default_self=True)

    # Status hashmap
    status_map: Final = {
        "online": "\U0001F7E2 (online)",
        "offline": "\U000026AB (offline)",
        "idle": "\U0001F7E1 (idle)",
        "dnd": "\U0001F534 (dnd)",
        "do_not_disturb": "\U0001F534 (dnd)",
        "invisible": "\U000026AB (offline)"
        }

    embed: Final = discord.Embed(title="User Information", description=f"User information for {user.mention}:", color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs))
    embed.set_thumbnail(url=user_avatar_url(user))
    embed.add_field(name="Username", value=str(user), inline=True)
    embed.add_field(name="User ID", value=str(user.id), inline=True)
    if member:
        embed.add_field(name="Status", value=status_map[member.raw_status], inline=True)
        embed.add_field(name="Highest Rank", value=f"{member.top_role.mention}", inline=True)
    embed.add_field(name="Created", value=parsedate(user.created_at), inline=True)
    if member:
        embed.add_field(name="Joined", value=parsedate(member.joined_at), inline=True)
        embed.add_field(name="Guild Perm Level", value=_get_highest_perm(message, member, ctx.conf_cache))

    # Parse adding infraction count
    with db_hlapi(message.guild.id) as db:
        viewinfs = parse_boolean(db.grab_config("member-view-infractions") or "0")
        moderator = await parse_permissions(message, ctx.conf_cache, "moderator", verbose=False)
        if moderator or (viewinfs and user.id == message.author.id):
            embed.add_field(name="Infractions", value=f"{db.grab_filter_infractions(user=user.id, count=True)}")

    embed.timestamp = Time.now().as_datetime()
    try:
        await message.channel.send(embed=embed)
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)


async def avatar_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    user, _ = await parse_user_member_noexcept(message, args, client, default_self=True)

    embed = discord.Embed(description=f"{user.mention}'s Avatar", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
    embed.set_image(url=user_avatar_url(user))
    embed.timestamp = Time.now().as_datetime()
    try:
        await message.channel.send(embed=embed)
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)


class Duration(int):
    """
    A duration represented as nanoseconds with helper methods for conversions
    """
    def micro(self) -> int:
        return self // 1000

    def milli(self) -> int:
        return self // 1000 // 1000

    def milli_f(self) -> float:
        return self / 1000 / 1000

    def sec(self) -> int:
        return self // 1000 // 1000 // 1000


# based on rusts std::time::Instant api
class Instant(int):
    @staticmethod
    def now() -> "Instant":
        return Instant(time.monotonic_ns())

    def elapsed(self) -> Duration:
        return Duration(time.monotonic_ns() - self)


class HelpHelper:
    __slots__ = "guild", "args", "client", "ctx", "prefix", "helpname", "message", "start_time"

    def __init__(self, message: discord.Message, guild: discord.Guild, args: List[str], client: discord.Client, ctx: CommandCtx, prefix: str, helpname: str, start_time: Instant):
        self.message = message
        self.guild = guild
        self.args = args
        self.client = client
        self.ctx = ctx
        self.prefix = prefix
        self.helpname = helpname
        self.start_time = start_time

    # Builds a single command
    async def single_command(self, cmd_name: str) -> discord.Embed:

        cmds_dict = self.ctx.cmds_dict

        # relies on true name for alias grouping
        if 'alias' in cmds_dict[cmd_name]:
            cmd_name = cmds_dict[cmd_name]['alias']

        command = SonnetCommand(cmds_dict[cmd_name])

        cmd_embed = discord.Embed(title=f'Command "{cmd_name}"', description=command.description, color=load_embed_color(self.guild, embed_colors.primary, self.ctx.ramfs))
        cmd_embed.set_author(name=self.helpname)

        cmd_embed.add_field(name="Usage:", value=self.prefix + command.pretty_name, inline=False)

        if "rich_description" in command:
            cmd_embed.add_field(name="Detailed information:", value=command.rich_description, inline=False)

        if isinstance(command.permission, str):
            perms = command.permission
        elif isinstance(command["permission"], (tuple, list)):
            perms = command.permission[0]
        else:
            perms = "NULL"

        hasperm = await parse_permissions(self.message, self.ctx.conf_cache, command.permission, verbose=False)
        permstr = f" (You {'do not '*(not hasperm)}have this perm)"

        cmd_embed.add_field(name="Permission level:", value=perms + permstr)

        aliases = ", ".join(filter(lambda c: "alias" in cmds_dict[c] and cmds_dict[c]["alias"] == cmd_name, cmds_dict))
        if aliases:
            cmd_embed.add_field(name="Aliases:", value=aliases, inline=False)

        module: lexdpyk.cmd_module = next(i for i in self.ctx.cmds if cmd_name in i.commands)

        cmd_embed.set_footer(text=f"Module: {module.category_info['pretty_name']} | Took: {self.start_time.elapsed().milli_f():.1f}ms")

        return cmd_embed

    # Builds help for a category
    async def category_help(self, category_name: str) -> Tuple[str, List[Tuple[str, str]], lexdpyk.cmd_module]:

        curmod = next(mod for mod in self.ctx.cmds if mod.category_info["name"] == category_name)
        nonAliasCommands = list(filter(lambda c: "alias" not in curmod.commands[c], curmod.commands))
        description = curmod.category_info["description"]
        override_commands: Optional[List[Tuple[str, str]]] = None

        if (override := getattr(curmod, "__help_override__", None)) is not None:
            newhelp: Optional[Tuple[str, List[Tuple[str, str]]]] = await CallCtx(override)(self.message, self.args, self.client, self.ctx)

            if newhelp is not None:
                description = newhelp[0]
                override_commands = newhelp[1]

        if override_commands is None:
            normal_commands: List[Tuple[str, str]] = []
            for i in sorted(nonAliasCommands):
                normal_commands.append((self.prefix + curmod.commands[i]['pretty_name'], curmod.commands[i]['description']))
            return description, normal_commands, curmod
        else:
            return description, override_commands, curmod

    async def full_help(self, page: int, per_page: int) -> discord.Embed:

        cmds = self.ctx.cmds
        cmds_dict = self.ctx.cmds_dict

        if page < 0 or page >= (len(self.ctx.cmds) + (per_page - 1)) // per_page:
            raise lib_sonnetcommands.CommandError(f"ERROR: No such page {page+1}")

        cmd_embed = discord.Embed(title=f"Category Listing (Page {page+1} / {(len(cmds) + (per_page-1))//per_page})", color=load_embed_color(self.guild, embed_colors.primary, self.ctx.ramfs))
        cmd_embed.set_author(name=self.helpname)

        total = 0
        # Total counting is separate due to pagination not counting all modules
        for cmd in cmds_dict:
            if 'alias' not in cmds_dict[cmd]:
                total += 1

        for module in sorted(cmds, key=lambda m: m.category_info['pretty_name'])[(page * per_page):(page * per_page) + per_page]:
            mnames = [f"`{i}`" for i in module.commands if 'alias' not in module.commands[i]]

            if mnames:
                builder = io.StringIO()
                for idx, i in enumerate(sorted(mnames)):
                    if idx != 0:
                        builder.write(", ")

                    if (len(i) + builder.tell()) < 512:
                        builder.write(i)
                    else:
                        builder.write("...")
                        break

                helptext = builder.getvalue()
            else:
                helptext = module.category_info['description']

            cmd_embed.add_field(name=f"{module.category_info['pretty_name']} ({module.category_info['name']})", value=helptext, inline=False)

        cmd_embed.set_footer(text=f"Total Commands: {total} | Total Endpoints: {len(cmds_dict)} | Took: {self.start_time.elapsed().milli_f():.1f}ms")

        return cmd_embed


async def help_function(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Any:
    if not message.guild:
        return 1

    start_time = Instant.now()

    helpname: str = f"{BOT_NAME} Help"
    per_page: int = 10

    cmds = ctx.cmds
    cmds_dict = ctx.cmds_dict

    parser = Parser("help")
    pageP = parser.add_arg(["-p", "--page"], lambda s: int(s) - 1)
    commandonlyP = parser.add_arg("-c", lib_tparse.store_true, flag=True)

    try:
        parser.parse(args, stderr=io.StringIO(), exit_on_fail=False, lazy=True, consume=True)
    except lib_tparse.ParseFailureError:
        raise lib_sonnetcommands.CommandError("Could not parse pagecount")

    page = pageP.get(0)
    commandonly = commandonlyP.get() is True

    prefix = ctx.conf_cache["prefix"]
    help_helper = HelpHelper(message, message.guild, args, client, ctx, prefix, helpname, start_time)

    if args:

        modules = {mod.category_info["name"] for mod in cmds}

        # Per module help
        if (a := args[0].lower()) in modules and not commandonly:

            description, commands, curmod = await help_helper.category_help(a)
            pagecount = (len(commands) + (per_page - 1)) // per_page

            cmd_embed = discord.Embed(
                title=f"{curmod.category_info['pretty_name']} (Page {page+1} / {pagecount})", description=description, color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs)
                )
            cmd_embed.set_author(name=helpname)

            if not (0 <= page < pagecount):  # pytype: disable=unsupported-operands
                raise lib_sonnetcommands.CommandError(f"ERROR: No such page {page+1}")

            for name, desc in commands[page * per_page:(page * per_page) + per_page]:
                cmd_embed.add_field(name=name, value=desc, inline=False)

            cmd_embed.set_footer(text=f"Module Version: {curmod.version_info} | Took {start_time.elapsed().milli_f():.1f}ms")

            try:
                await message.channel.send(embed=cmd_embed)
            except discord.errors.Forbidden:
                raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)

        # Per command help
        elif a in cmds_dict:
            try:
                await message.channel.send(embed=await help_helper.single_command(a))
            except discord.errors.Forbidden:
                raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)

        # Do not echo user input
        else:
            # lets check if they can't read documentation
            probably_tried_paging: bool
            try:
                probably_tried_paging = int(args[0]) <= ((len(cmds) + (per_page - 1)) // per_page)
            except ValueError:
                probably_tried_paging = False

            no_command_text: str = f"No command {'or command module '*(not commandonly)}with that name"

            if probably_tried_paging:
                raise lib_sonnetcommands.CommandError(f"{no_command_text} (did you mean `{prefix}help -p {int(args[0])}`?)")

            raise lib_sonnetcommands.CommandError(no_command_text)

    # Total help
    else:

        try:
            await message.channel.send(embed=await help_helper.full_help(page, per_page))
        except discord.errors.Forbidden:
            raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)


async def grab_guild_info(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    guild = message.guild

    embed_col = load_embed_color(guild, embed_colors.primary, kwargs["ramfs"])

    guild_embed = discord.Embed(title=f"Information on {guild}", color=embed_col)
    if guild.owner:
        guild_embed.add_field(name="Server Owner:", value=guild.owner.mention)
    guild_embed.add_field(name="# of Roles:", value=f"{len(guild.roles)} Roles")
    guild_embed.add_field(name="Top Role:", value=guild.roles[-1].mention)
    guild_embed.add_field(name="Member Count:", value=str(guild.member_count))
    guild_embed.add_field(name="Creation Date:", value=parsedate(guild.created_at))

    guild_embed.set_footer(text=f"gid: {guild.id}")
    guild_embed.set_thumbnail(url=cast(str, guild.icon_url))

    try:
        await message.channel.send(embed=guild_embed)
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)


def perms_to_str(p: discord.Permissions) -> str:
    values: List[str] = []
    for i, v in constants.permission.name_offsets.items():
        if (1 << i & p.value) == 1 << i:
            values.append(v)

    values.sort()

    if values:
        return f"`{'` `'.join(values)}`"
    else:
        return "None"


async def grab_role_info(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    if not args:
        raise lib_sonnetcommands.CommandError(constants.sonnet.error_args.not_enough)

    try:
        role_id = int(args[0].strip("<@&>"))
    except ValueError:
        raise lib_sonnetcommands.CommandError("ERROR: Could not parse role id")

    if (role := message.guild.get_role(role_id)) is not None:

        r_embed = discord.Embed(title="Role Info", description=f"Information on {role.mention}", color=load_embed_color(message.guild, "primary", ctx.ramfs))
        r_embed.add_field(name="User Count", value=str(len(role.members)), inline=False)
        r_embed.add_field(name=f"Permissions ({role.permissions.value})", value=perms_to_str(role.permissions))

        r_embed.set_footer(text=f"id: {role.id}")
        r_embed.timestamp = Time.now().as_datetime()

        try:
            await message.channel.send(embed=r_embed)
        except discord.errors.Forbidden:
            raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)

        return 0

    else:
        raise lib_sonnetcommands.CommandError("ERROR: Could not grab role from this guild")


async def grab_guild_message(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> int:
    if not message.guild:
        return 1

    discord_message: discord.Message

    discord_message, nargs = await parse_channel_message_noexcept(message, args, client)

    if not discord_message.guild or isinstance(discord_message.channel, (discord.DMChannel, discord.GroupChannel)):
        raise lib_sonnetcommands.CommandError("ERROR: Message not in any guild")

    if not isinstance(message.author, discord.Member):
        raise lib_sonnetcommands.CommandError("ERROR: The user that ran this command is no longer in the guild?")

    # do extra validation that they can see this message
    if not discord_message.channel.permissions_for(message.author).read_messages:
        raise lib_sonnetcommands.CommandError("ERROR: You do not have permission to view this message")

    sendraw = False
    for arg in args[nargs:]:
        if arg in ["-r", "--raw"]:
            sendraw = True
            break

    # Generate replies
    message_content = generate_reply_field(discord_message)

    # Message has been grabbed, start generating embed
    message_embed = discord.Embed(title=f"Message in #{discord_message.channel}", description=message_content, color=load_embed_color(message.guild, embed_colors.primary, ctx.ramfs))

    message_embed.set_author(name=str(discord_message.author), icon_url=user_avatar_url(discord_message.author))
    message_embed.timestamp = discord_message.created_at

    # Grab files from cache
    fileobjs = grab_files(discord_message.guild.id, discord_message.id, ctx.kernel_ramfs)

    # Grab files async if not in cache
    if fileobjs is None:
        awaitobjs = [asyncio.create_task(i.to_file()) for i in discord_message.attachments]
        fileobjs = [await i for i in awaitobjs]

    if sendraw:
        file_content = io.BytesIO(discord_message.content.encode("utf8"))
        fileobjs.append(discord.File(file_content, filename=f"{discord_message.id}.at.{Time.now().unix()}.txt"))

    try:
        await message.channel.send(embed=message_embed, files=fileobjs)
    except discord.errors.HTTPException:
        try:
            await message.channel.send("There were files attached but they exceeded the guild filesize limit", embed=message_embed)
        except discord.errors.Forbidden:
            raise lib_sonnetcommands.CommandError(constants.sonnet.error_embed)

    return 0


async def initialise_poll(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:

    try:
        await message.add_reaction("\U0001F44D")  # Thumbs up emoji
        await message.add_reaction("\U0001F44E")  # Thumbs down emoji
    except discord.errors.Forbidden:
        raise lib_sonnetcommands.CommandError("ERROR: The bot does not have permissions to add a reaction here")
    except discord.errors.NotFound:
        raise lib_sonnetcommands.CommandError("ERROR: Could not find the message [404]")


async def coinflip(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> None:

    # take the answer first to instill disappointment that nothing is truly random
    out = f"Flipping a coin... {random.choice(['Heads!','Tails!'])}"

    if ctx.verbose:
        mobj = await message.channel.send("Flipping a coin...")
        await asyncio.sleep(random.randint(500, 1000) / 1000)
        await mobj.edit(content=out)
    else:
        # dont bother with sleeps if we are being called as a subcommand
        await message.channel.send(out)


category_info = {'name': 'utilities', 'pretty_name': 'Utilities', 'description': 'Utility commands.'}

commands = {
    'roleinfo': {
        'alias': 'role-info'
        },
    'role-info': {
        'pretty_name': 'role-info <role>',
        'description': 'Get information on a role',
        'permission': 'everyone',
        'execute': grab_role_info,
        },
    'ping': {
        'pretty_name': 'ping',
        'description': 'Test connection to bot',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': ping_function
        },
    'user-info': {
        'alias': 'profile'
        },
    'userinfo': {
        'alias': 'profile'
        },
    'profile': {
        'pretty_name': 'profile [user]',
        'description': 'Get a users profile',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': profile_function
        },
    'help':
        {
            'pretty_name': 'help [category|command] [-p PAGE] [-c]',
            'description': 'Print helptext, `-c` designates to only look for a command',
            'rich_description': 'Gives permission level, aliases (if any), and detailed information (if any) on specific command lookups',
            'execute': help_function
            },
    'pfp': {
        'alias': 'avatar'
        },
    'avatar': {
        'pretty_name': 'avatar [user]',
        'description': 'Get avatar of a user',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': avatar_function
        },
    'server-info': {
        'alias': 'serverinfo'
        },
    'serverinfo': {
        'pretty_name': 'serverinfo',
        'description': 'Get info on this guild',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': grab_guild_info
        },
    'get-message': {
        'alias': 'grab-message'
        },
    'grab-message': {
        'pretty_name': 'grab-message <message> [-r]',
        'description': 'Grab a message and show its contents, specify -r to get message content as a file',
        'execute': grab_guild_message
        },
    'poll': {
        'pretty_name': 'poll',
        'description': 'Start a reaction based poll on the message',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': initialise_poll
        },
    'coinflip': {
        'pretty_name': 'coinflip',
        'description': 'Flip a coin',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': coinflip
        }
    }

version_info: str = "1.2.14-DEV"
