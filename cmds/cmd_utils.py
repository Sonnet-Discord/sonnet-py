# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import importlib

import discord, time, asyncio, random
from datetime import datetime

import sonnet_cfg

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_parsers
importlib.reload(lib_parsers)

from lib_db_obfuscator import db_hlapi
from lib_parsers import parse_permissions


async def parse_userid(message, args):

    # Get user ID from the message, otherwise use the author's ID.
    try:
        id_to_probe = int(args[0].strip("<@!>"))
    except IndexError:
        id_to_probe = message.author.id
    except ValueError:
        await message.channel.send("Invalid userid")
        raise RuntimeError

    # Get the Member object by user ID, otherwise fail.
    user_object = message.guild.get_member(id_to_probe)

    if not user_object:
        await message.channel.send("Invalid userid")
        raise RuntimeError

    return user_object


async def ping_function(message, args, client, **kwargs):
    stats = kwargs["stats"]
    ping_embed = discord.Embed(title="Pong!", description="Connection between Sonnet and Discord is OK", color=0x00ff6e)
    ping_embed.add_field(name="Total Process Time", value=str((stats["end"] - stats["start"]) / 100) + "ms", inline=False)
    ping_embed.add_field(name="Load Configs", value=str((stats["end-load-blacklist"] - stats["start-load-blacklist"]) / 100) + "ms", inline=False)
    ping_embed.add_field(name="Process Automod", value=str((stats["end-automod"] - stats["start-automod"]) / 100) + "ms", inline=False)
    time_to_send = round(time.time() * 10000)
    sent_message = await message.channel.send(embed=ping_embed)
    ping_embed.add_field(name="Send Message", value=str((round(time.time() * 10000) - time_to_send) / 100) + "ms", inline=False)
    await sent_message.edit(embed=ping_embed)


async def profile_function(message, args, client, **kwargs):

    try:
        user_object = await parse_userid(message, args)
    except RuntimeError:
        return

    # Status hashmap
    status_map = {"online": "🟢", "offline": "⚫", "idle": "🟡", "dnd": "🔴", "do_not_disturb": "🔴", "invisible": "⚫"}

    # Put here to comply with formatting guidelines.
    created_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(user_object.created_at)))
    created_string += f" ({(datetime.utcnow() - user_object.created_at).days} days ago)"

    joined_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(user_object.joined_at)))
    joined_string += f" ({(datetime.utcnow() - user_object.joined_at).days} days ago)"

    embed = discord.Embed(title="User Information", description=f"Cached user information for {user_object.mention}:", color=0x758cff)
    embed.set_thumbnail(url=user_object.avatar_url)
    embed.add_field(name="Username", value=user_object.name + "#" + user_object.discriminator, inline=True)
    embed.add_field(name="User ID", value=user_object.id, inline=True)
    embed.add_field(name="Status", value=status_map[user_object.raw_status], inline=True)
    embed.add_field(name="Highest Rank", value=f"{user_object.top_role.mention}", inline=True)
    embed.add_field(name="Created", value=created_string, inline=True)
    embed.add_field(name="Joined", value=joined_string, inline=True)

    # Parse adding infraction count
    with db_hlapi(message.guild.id) as db:
        viewinfs = db.grab_config("member-view-infractions")
        if viewinfs:
            viewinfs = bool(int(viewinfs))
        else:
            viewinfs = False
        moderator = await parse_permissions(message, kwargs["conf_cache"], "moderator", verbose=False)
        if moderator or (viewinfs and user_object.id == message.author.id):
            embed.add_field(name="Infractions", value=f"{len(db.grab_user_infractions(user_object.id))}")

    embed.timestamp = datetime.utcnow()
    await message.channel.send(embed=embed)


async def avatar_function(message, args, client, **kwargs):

    try:
        user_object = await parse_userid(message, args)
    except RuntimeError:
        return

    embed = discord.Embed(description=f"{user_object.mention}'s Avatar", color=0x758cff)
    embed.set_image(url=user_object.avatar_url)
    embed.timestamp = datetime.utcnow()
    await message.channel.send(embed=embed)


async def help_function(message, args, client, **kwargs):

    if args:

        modules = {mod.category_info["name"] for mod in kwargs["cmds"]}
        PREFIX = kwargs["conf_cache"]["prefix"]

        # Per module help
        if (a := args[0].lower()) in modules:

            curmod = [mod for mod in kwargs["cmds"] if mod.category_info["name"] == a][0]
            cmd_embed = discord.Embed(title=f'Commands in Category "{a}"', color=0x00db87)
            cmd_embed.set_author(name="Sonent Help")

            for i in filter(lambda c: "alias" not in curmod.commands[c], curmod.commands.keys()):
                cmd_embed.add_field(name=PREFIX + curmod.commands[i]['pretty_name'], value=curmod.commands[i]['description'], inline=False)

            await message.channel.send(embed=cmd_embed)

        # Per command help
        elif a in kwargs["cmds_dict"]:
            if "alias" in kwargs["cmds_dict"][a]:
                a = kwargs["cmds_dict"][a]["alias"]

            cmd_embed = discord.Embed(title=f'Command "{a}"', description=kwargs["cmds_dict"][a]['description'], color=0x00db87)
            cmd_embed.set_author(name="Sonent Help")

            cmd_embed.add_field(name="Usage:", value=PREFIX + kwargs["cmds_dict"][a]["pretty_name"], inline=False)

            if "rich_description" in kwargs["cmds_dict"][a]:
                cmd_embed.add_field(name="Detailed information:", value=kwargs["cmds_dict"][a]["rich_description"], inline=False)

            aliases = list(filter(lambda c: "alias" in kwargs["cmds_dict"][c] and kwargs["cmds_dict"][c]["alias"] == a, kwargs["cmds_dict"]))
            if aliases:
                cmd_embed.add_field(name="Aliases:", value=", ".join(aliases), inline=False)

            await message.channel.send(embed=cmd_embed)

        # Do not echo user input
        else:
            await message.channel.send("No command or command module with that name")

    # Total help
    else:

        cmd_embed = discord.Embed(title="Category Listing", color=0x00db87)
        cmd_embed.set_author(name="Sonnet Help")

        for modules in kwargs["cmds"]:
            cmd_embed.add_field(name=f"{modules.category_info['pretty_name']} ({modules.category_info['name']})", value=modules.category_info['description'], inline=False)

        await message.channel.send(embed=cmd_embed)


async def grab_guild_info(message, args, client, **kwargs):

    guild = message.channel.guild

    created_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(guild.created_at)))
    created_string += f" ({(datetime.utcnow() - guild.created_at).days} days ago)"

    guild_embed = discord.Embed(title=f"Information on {guild}", color=0x00ff6e)
    guild_embed.add_field(name="Server Owner:", value=guild.owner.mention)
    guild_embed.add_field(name="# of Roles:", value=f"{len(guild.roles)} Roles")
    guild_embed.add_field(name="Top Role:", value=str(guild.roles[-1]))
    guild_embed.add_field(name="Member Count:", value=str(guild.member_count))
    guild_embed.add_field(name="Creation Date:", value=created_string)
    guild_embed.set_thumbnail(url=guild.icon_url)

    await message.channel.send(embed=guild_embed)


async def initialise_poll(message, args, client, **kwargs):

    try:
        await message.add_reaction("👍")
        await message.add_reaction("👎")
    except discord.errors.Forbidden:
        await message.channel.send("The bot does not have permissions to add a reaction here")


async def coinflip(message, args, client, **kwargs):

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
    'help': {
        'pretty_name': 'help [category|command]',
        'description': 'Print helptext',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': help_function
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

version_info = "1.2.0-DEV"
