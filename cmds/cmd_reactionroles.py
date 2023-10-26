# Reactionroles settings
# Ultrabear 2021

import importlib

import discord
import json, io, asyncio

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_parsers

importlib.reload(lib_parsers)
import lib_loaders

importlib.reload(lib_loaders)
import lib_compatibility

importlib.reload(lib_compatibility)

from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_channel_message_noexcept
from lib_loaders import load_embed_color, embed_colors
from lib_compatibility import to_snowflake

from typing import List, Any, Final, Dict, Union

# This is imposed due to the projected database failure beyond ~1500 reactionroles (due to a 65k char limit on configs)
# This may be increased if predictions are improved or the db is upgraded
REACTIONROLE_SANITY_LIMIT: Final = 750


class InvalidEmoji(Exception):
    __slots__ = ()


# NOTE(ultrabear): reactionrole data used to be stored in the form Dict[str(message_id), Dict[str(unicode or emoji str), role_id]]
# it is now stored in the form Dict[str(message_id), Dict[str(unicode or emoji_id), role_id]]
# to maintain backwards compatibility the remove_reactionroles function still attempts to remove the string format, and the dlib module will still attempt to load emoji str repr
# but the add functions will only use the new format


async def valid_emoji(message: discord.Message, pEmoji: str, client: discord.Client) -> Union[str, discord.Emoji]:

    if len(pEmoji) <= 5:
        return pEmoji
    else:

        try:
            em = int(pEmoji.split(":")[-1].rstrip(">"))
        except ValueError:
            await message.channel.send("ERROR: Could not validate emoji")
            raise InvalidEmoji

        emoji = client.get_emoji(em)

        if not emoji:
            await message.channel.send("ERROR: Emoji does not exist in scope")
            raise InvalidEmoji

        return emoji


class RindexFailure(Exception):
    __slots__ = ()


async def rindex_check(message: discord.Message, role: discord.Role) -> None:
    if not message.guild or not isinstance(message.author, discord.Member):
        raise RindexFailure("No guild roles/No user")

    rindex = message.guild.roles.index(role)

    if rindex >= message.guild.roles.index(message.author.roles[-1]):
        await message.channel.send("ERROR: Cannot autorole a role that is higher or the same as your current top role")
        raise RindexFailure
    elif rindex >= message.guild.roles.index(message.guild.me.roles[-1]):
        await message.channel.send("ERROR: Cannot autorole a role that is higher or the same as this bots top role")
        raise RindexFailure


class NoRoleError(Exception):
    __slots__ = ()


async def get_exact_role(message: discord.Message, rolestr: str) -> discord.Role:
    if not message.guild:
        raise NoRoleError("No Guild to parse role from")

    try:
        role = message.guild.get_role(int(rolestr.strip("<@&>")))
    except ValueError:
        await message.channel.send("ERROR: Invalid role")
        raise NoRoleError

    if not role:
        await message.channel.send("ERROR: Invalid role")
        raise NoRoleError

    return role


async def try_add_reaction(message: discord.Message, emoji: Union[discord.Emoji, str]) -> None:
    try:
        await message.add_reaction(emoji)
    except discord.errors.Forbidden:
        # raise non permission errors
        pass


async def try_remove_reaction(me: discord.Client, message: discord.Message, emoji: Union[discord.Emoji, str]) -> None:
    if not me.user:
        return

    try:
        await message.remove_reaction(emoji, to_snowflake(me.user))
    except discord.errors.Forbidden:
        # raise non permission errors
        pass


async def add_reactionroles(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    rr_message, nargs = await parse_channel_message_noexcept(message, args, client)

    args = args[nargs:]

    if len(args) < 2:
        await message.channel.send("ERROR: Not enough args supplied")
        return 1

    try:
        emoji = await valid_emoji(message, args[0], client)
        role = await get_exact_role(message, args[1])
        await rindex_check(message, role)
    except (InvalidEmoji, NoRoleError, RindexFailure):
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles: Dict[str, Dict[str, int]] = json.loads(db.grab_config("reaction-role-data") or "{}")

    rrcount = sum(len(v) for _, v in reactionroles.items())

    if rrcount >= REACTIONROLE_SANITY_LIMIT:
        await message.channel.send("ERROR: Reached sanity limit of {REACTIONROLE_SANITY_LIMIT} total reactionroles, if you wish to add more then remove others")
        return 1

    if str(rr_message.id) not in reactionroles:
        reactionroles[str(rr_message.id)] = {}

    # overload cond, because we store a different format for the same role potentially you can have 2 roles from one emoji,
    # this is a bug that can be mitigated by using remove_reactionroles for the emoji and resetting it to only one role
    reactionroles[str(rr_message.id)][emoji if isinstance(emoji, str) else str(emoji.id)] = role.id

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    await try_add_reaction(rr_message, emoji)

    if kwargs["verbose"]: await message.channel.send(f"Added reactionrole to message id {rr_message.id}: {emoji}:{role.mention}", allowed_mentions=discord.AllowedMentions.none())


async def remove_reactionroles(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    rr_message, nargs = await parse_channel_message_noexcept(message, args, client)

    args = args[nargs:]

    if not args:
        await message.channel.send("ERROR: Not enough args supplied")
        return 1

    try:
        emoji = await valid_emoji(message, args[0], client)
    except InvalidEmoji:
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles_raw = db.grab_config("reaction-role-data")

    if not reactionroles_raw:
        await message.channel.send("ERROR: This guild has no reactionroles")
        return 1

    reactionroles: Dict[str, Dict[str, int]] = json.loads(reactionroles_raw)

    if str(rr_message.id) in reactionroles:
        if str(emoji) in reactionroles[str(rr_message.id)]:
            del reactionroles[str(rr_message.id)][str(emoji)]
        elif isinstance(emoji, discord.Emoji) and any(i in reactionroles[str(rr_message.id)] for i in (str(emoji.id), str(emoji))):
            try:
                # try deleting old repr
                del reactionroles[str(rr_message.id)][str(emoji)]
            except KeyError:
                pass
            try:
                # try deleting new repr
                del reactionroles[str(rr_message.id)][str(emoji.id)]
            except KeyError:
                pass
        else:
            await message.channel.send(f"ERROR: This message does not have {emoji} reactionrole on it")
            return 1

        # cleanup fragments from json store
        if len(reactionroles[str(rr_message.id)]) == 0:
            del reactionroles[str(rr_message.id)]

        await try_remove_reaction(client, rr_message, emoji)

    else:
        await message.channel.send("ERROR: This message has no reactionroles on it")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Removed reactionrole {emoji} from message id {rr_message.id}")


async def list_reactionroles(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    with db_hlapi(message.guild.id) as db:
        data: Dict[str, Dict[str, int]] = json.loads(db.grab_config("reaction-role-data") or "{}")

    reactionrole_embed = discord.Embed(title=f"ReactionRoles in {message.guild}", color=load_embed_color(message.guild, embed_colors.primary, kwargs["ramfs"]))

    items = list(filter(lambda kv: len(kv[1]), data.items()))

    if items:

        if len(items) <= 20:
            for k, v in items:
                reactionrole_embed.add_field(name=k, value="\n".join([f"{emoji}: <@&{v[emoji]}>" for emoji in v]))

            await message.channel.send(embed=reactionrole_embed)

        else:

            fileobj = io.BytesIO()
            fileobj.write(json.dumps(data).encode("utf8"))
            fileobj.seek(0)
            dfile = discord.File(fileobj, filename="RR.json")
            await message.channel.send("Too many rr messages to send in embed", file=dfile)

    else:
        await message.channel.send("This guild has no reactionroles")


async def addmany_reactionroles(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    rr_message: discord.Message
    nargs: int

    rr_message, nargs = await parse_channel_message_noexcept(message, args, client)

    args = args[nargs:]

    with db_hlapi(message.guild.id) as db:
        reactionroles: Dict[str, Dict[str, int]] = json.loads(db.grab_config("reaction-role-data") or "{}")

    for i in range(len(args) // 2):
        try:
            emoji = await valid_emoji(message, args[i * 2], client)
            role = await get_exact_role(message, args[i * 2 + 1])
            await rindex_check(message, role)
        except (InvalidEmoji, NoRoleError, RindexFailure):
            return 1

        if str(rr_message.id) not in reactionroles:
            reactionroles[str(rr_message.id)] = {}

        reactionroles[str(rr_message.id)][emoji if isinstance(emoji, str) else str(emoji.id)] = role.id

        asyncio.create_task(try_add_reaction(rr_message, emoji))

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send("Added Multiple reactionroles")


async def rr_purge(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:
    if not message.guild:
        return 1

    try:
        message_id = int(args[0].replace("-", "/").split("/")[-1])
    except IndexError:
        await message.channel.send("ERROR: No message id supplied")
        return 1
    except ValueError:
        await message.channel.send("ERROR: Message id is not a valid int")
        return 1

    with db_hlapi(message.guild.id) as db:
        reactionroles_raw = db.grab_config("reaction-role-data")

    if not reactionroles_raw:
        await message.channel.send("ERROR: This guild has no reactionroles")
        return 1

    reactionroles: Dict[str, Dict[str, int]] = json.loads(reactionroles_raw)

    if str(message_id) in reactionroles:
        del reactionroles[str(message_id)]
    else:
        await message.channel.send("ERROR: This message has no reactionroles")
        return 1

    with db_hlapi(message.guild.id) as db:
        db.add_config("reaction-role-data", json.dumps(reactionroles))

    if kwargs["verbose"]: await message.channel.send(f"Purged reactionroles from message with id {message_id}")


category_info = {'name': 'rr', 'pretty_name': 'Reaction Roles', 'description': 'Commands for controlling Reaction Role settings'}

commands = {
    'rr-add': {
        'pretty_name': 'rr-add <message> <emoji> <role>',
        'description': 'Add a reactionrole to a message',
        'permission': 'administrator',
        'cache': 'regenerate',
        'execute': add_reactionroles
        },
    'rr-purge':
        {
            'pretty_name': 'rr-purge <message id>',
            'description': 'Purge all reactionroles from a message',
            'rich_description': 'Currently the only way to remove reactionroles from a deleted message',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': rr_purge
            },
    'rr-rm': {
        'alias': 'rr-remove'
        },
    'rr-remove':
        {
            'pretty_name': 'rr-remove <message> <emoji>',
            'description': 'Remove a reactionrole from a message',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': remove_reactionroles
            },
    'rr-ls': {
        'alias': 'rr-list'
        },
    'rr-list':
        {
            'pretty_name': 'rr-list',
            'description': 'List all reactionroles in guild',
            'rich_description': 'Does not display in guilds with more than 25 messages, will instead drop a file',
            'permission': 'administrator',
            'cache': 'keep',
            'execute': list_reactionroles
            },
    'rr-addmany':
        {
            'pretty_name': 'rr-addmany <message> (?:<emoji> <role>)+',
            'description': 'Add multiple reactionroles',
            'rich_description': 'Multiple reactionroles can be space or newline separated',
            'permission': 'administrator',
            'cache': 'regenerate',
            'execute': addmany_reactionroles
            },
    }

version_info: str = "2.0.2-DEV"
