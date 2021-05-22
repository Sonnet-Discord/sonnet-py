# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import importlib

import discord, time, asyncio, random
from datetime import datetime

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)
import lib_constants

importlib.reload(lib_constants)

from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_permissions, parse_boolean
from lib_loaders import load_embed_color, embed_colors
import lib_constants as constants

from typing import List, Any


class UserParseError(RuntimeError):
    pass


async def parse_userid(message: discord.Message, args: List[str]) -> discord.Member:

    # Get user ID from the message, otherwise use the author's ID.
    try:
        id_to_probe = int(args[0].strip("<@!>"))
    except IndexError:
        id_to_probe = message.author.id
    except ValueError:
        await message.channel.send("Invalid userid")
        raise UserParseError

    # Get the Member object by user ID, otherwise fail.
    user_object = message.guild.get_member(id_to_probe)

    if not user_object:
        await message.channel.send("Invalid userid")
        raise UserParseError

    return user_object


def add_timestamp(embed: discord.Embed, name: str, start: int, end: int) -> None:
    embed.add_field(name=name, value=f"{(end - start) / 100}ms", inline=False)


def ctime(t: float) -> int:
    return round(t * 100000)


async def ping_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

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


def parsedate(indata: datetime) -> str:
    return f"{time.strftime('%a, %d %b %Y %H:%M:%S', indata.utctimetuple())} ({(datetime.utcnow() - indata).days} days ago)"


async def profile_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        user_object = await parse_userid(message, args)
    except UserParseError:
        return 1

    # Status hashmap
    status_map = {"online": "🟢 (online)", "offline": "⚫ (offline)", "idle": "🟡 (idle)", "dnd": "🔴 (dnd)", "do_not_disturb": "🔴 (dnd)", "invisible": "⚫ (offline)"}

    embed = discord.Embed(title="User Information", description=f"User information for {user_object.mention}:", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
    embed.set_thumbnail(url=user_object.avatar_url)
    embed.add_field(name="Username", value=user_object.name + "#" + user_object.discriminator, inline=True)
    embed.add_field(name="User ID", value=user_object.id, inline=True)
    embed.add_field(name="Status", value=status_map[user_object.raw_status], inline=True)
    embed.add_field(name="Highest Rank", value=f"{user_object.top_role.mention}", inline=True)
    embed.add_field(name="Created", value=parsedate(user_object.created_at), inline=True)
    embed.add_field(name="Joined", value=parsedate(user_object.joined_at), inline=True)

    # Parse adding infraction count
    with db_hlapi(message.guild.id) as db:
        viewinfs = parse_boolean(db.grab_config("member-view-infractions") or "0")
        moderator = await parse_permissions(message, kwargs["conf_cache"], "moderator", verbose=False)
        if moderator or (viewinfs and user_object.id == message.author.id):
            embed.add_field(name="Infractions", value=f"{len(db.grab_user_infractions(user_object.id))}")

    embed.timestamp = datetime.utcnow()
    try:
        await message.channel.send(embed=embed)
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def avatar_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        user_object = await parse_userid(message, args)
    except UserParseError:
        return 1

    embed = discord.Embed(description=f"{user_object.mention}'s Avatar", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
    embed.set_image(url=user_object.avatar_url)
    embed.timestamp = datetime.utcnow()
    try:
        await message.channel.send(embed=embed)
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1


async def help_function(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    helpname: str = "Sonnet Help"

    if args:

        modules = {mod.category_info["name"] for mod in kwargs["cmds"]}
        PREFIX = kwargs["conf_cache"]["prefix"]

        # Per module help
        if (a := args[0].lower()) in modules:

            curmod = [mod for mod in kwargs["cmds"] if mod.category_info["name"] == a][0]
            cmd_embed = discord.Embed(
                title=curmod.category_info["pretty_name"], description=curmod.category_info["description"], color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"])
                )
            cmd_embed.set_author(name=helpname)

            for i in filter(lambda c: "alias" not in curmod.commands[c], curmod.commands.keys()):
                cmd_embed.add_field(name=PREFIX + curmod.commands[i]['pretty_name'], value=curmod.commands[i]['description'], inline=False)

            try:
                await message.channel.send(embed=cmd_embed)
            except discord.errors.Forbidden:
                await message.channel.send(constants.sonnet.error_embed)
                return 1

        # Per command help
        elif a in kwargs["cmds_dict"]:
            if "alias" in kwargs["cmds_dict"][a]:
                a = kwargs["cmds_dict"][a]["alias"]

            cmd_embed = discord.Embed(title=f'Command "{a}"', description=kwargs["cmds_dict"][a]['description'], color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
            cmd_embed.set_author(name=helpname)

            cmd_embed.add_field(name="Usage:", value=PREFIX + kwargs["cmds_dict"][a]["pretty_name"], inline=False)

            if "rich_description" in kwargs["cmds_dict"][a]:
                cmd_embed.add_field(name="Detailed information:", value=kwargs["cmds_dict"][a]["rich_description"], inline=False)

            if (t := type(kwargs["cmds_dict"][a]["permission"])) == str:
                perms = kwargs["cmds_dict"][a]["permission"]
            elif t == tuple or t == list:
                perms = kwargs["cmds_dict"][a]["permission"][0]
            else:
                perms = "NULL"

            cmd_embed.add_field(name="Permission level:", value=perms)

            aliases = ", ".join(filter(lambda c: "alias" in kwargs["cmds_dict"][c] and kwargs["cmds_dict"][c]["alias"] == a, kwargs["cmds_dict"]))
            if aliases:
                cmd_embed.add_field(name="Aliases:", value=aliases, inline=False)

            try:
                await message.channel.send(embed=cmd_embed)
            except discord.errors.Forbidden:
                await message.channel.send(constants.sonnet.error_embed)
                return 1

        # Do not echo user input
        else:
            await message.channel.send("No command or command module with that name")
            return 1

    # Total help
    else:

        cmd_embed = discord.Embed(title="Category Listing", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))
        cmd_embed.set_author(name=helpname)

        total = 0

        for module in kwargs["cmds"]:
            mnames = [f"`{i}`" for i in module.commands if 'alias' not in module.commands[i]]
            helptext = ', '.join(mnames)
            total += len(mnames)
            cmd_embed.add_field(name=f"{module.category_info['pretty_name']} ({module.category_info['name']})", value=helptext, inline=False)

        cmd_embed.set_footer(text=f"Total Commands: {total} | Total Endpoints: {len(kwargs['cmds_dict'])}")

        try:
            await message.channel.send(embed=cmd_embed)
        except discord.errors.Forbidden:
            await message.channel.send(constants.sonnet.error_embed)
            return 1


async def grab_guild_info(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    guild = message.guild

    embed_col = load_embed_color(guild, embed_colors.primary, kwargs["ramfs"])

    guild_embed = discord.Embed(title=f"Information on {guild}", color=embed_col)
    guild_embed.add_field(name="Server Owner:", value=guild.owner.mention)
    guild_embed.add_field(name="# of Roles:", value=f"{len(guild.roles)} Roles")
    guild_embed.add_field(name="Top Role:", value=guild.roles[-1].mention)
    guild_embed.add_field(name="Member Count:", value=str(guild.member_count))
    guild_embed.add_field(name="Creation Date:", value=parsedate(guild.created_at))

    guild_embed.set_footer(text=f"gid: {guild.id}")
    guild_embed.set_thumbnail(url=guild.icon_url)

    try:
        await message.channel.send(embed=guild_embed)
    except discord.errors.Forbidden:
        await message.channel.send(constants.sonnet.error_embed)
        return 1

async def initialise_poll(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    try:
        await message.add_reaction("👍")
        await message.add_reaction("👎")
    except discord.errors.Forbidden:
        await message.channel.send("ERROR: The bot does not have permissions to add a reaction here")
        return 1
    except discord.errors.NotFound:
        await message.channel.send("ERROR: Could not find the message [404]")
        return 1


async def coinflip(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    mobj = await message.channel.send("Flipping a coin...")
    await asyncio.sleep(random.randint(500, 1000) / 1000)
    await mobj.edit(content=f"Flipping a coin... {random.choice(['Heads!','Tails!'])}")


category_info = {'name': 'utilities', 'pretty_name': 'Utilities', 'description': 'Utility commands.'}

commands = {
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
            'pretty_name': 'help [category|command]',
            'description': 'Print helptext',
            'rich_description': 'Gives permission level, aliases (if any), and detailed information (if any) on specific command lookups',
            'permission': 'everyone',
            'cache': 'keep',
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

version_info: str = "1.2.5-DEV"
