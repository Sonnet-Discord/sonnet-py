# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import discord
from datetime import datetime
import time
import sonnet_cfg

from lib_loaders import load_message_config

from lib_db_obfuscator import db_hlapi


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
    # Secondary catch if actually getting the member succeeds but passes nothing to the variable.
    if not user_object:
        await message.channel.send("Invalid userid")
        raise RuntimeError

    return user_object


async def ping_function(message, args, client, stats, cmds, ramfs):
    ping_embed = discord.Embed(title="Pong!", description="Connection between Sonnet and Discord is OK", color=0x00ff6e)
    ping_embed.add_field(name="Total Process Time", value=str((stats["end"] - stats["start"])/100) + "ms", inline=False)
    ping_embed.add_field(name="Load Configs", value=str((stats["end-load-blacklist"] - stats["start-load-blacklist"])/100) + "ms", inline=False)
    ping_embed.add_field(name="Process Blacklist", value=str((stats["end-blacklist"] - stats["start-blacklist"])/100) + "ms", inline=False)
    time_to_send = round(time.time()*10000)
    sent_message = await message.channel.send(embed=ping_embed)
    ping_embed.add_field(name="Send Message", value=str((round(time.time()*10000) - time_to_send)/100) + "ms", inline=False)
    await sent_message.edit(embed=ping_embed)


async def profile_function(message, args, client, stats, cmds, ramfs):

    try:
        user_object = await parse_userid(message, args)
    except RuntimeError:
        return

    # Put here to comply with formatting guidelines.
    created_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(user_object.created_at)))
    created_string += f" ({(datetime.utcnow() - user_object.created_at).days} days ago)"

    joined_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(user_object.joined_at)))
    joined_string += f" ({(datetime.utcnow() - user_object.joined_at).days} days ago)"
    embed=discord.Embed(title="User Information", description=f"Cached user information for {user_object.mention}:", color=0x758cff)
    embed.set_thumbnail(url=user_object.avatar_url)
    embed.add_field(name="Username", value=user_object.name + "#" + user_object.discriminator, inline=True)
    embed.add_field(name="User ID", value=user_object.id, inline=True)
    embed.add_field(name="Status", value=user_object.raw_status, inline=True)
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
        moderator = message.author.permissions_in(message.channel).kick_members
        if moderator or (viewinfs and user_object.id == message.author.id):
            embed.add_field(name="Infractions", value=f"{len(db.grab_user_infractions(user_object.id))}")

    embed.timestamp = datetime.utcnow()
    await message.channel.send(embed=embed)


async def avatar_function(message, args, client, stats, cmd_modules, ramfs):

    try:
        user_object = await parse_userid(message, args)
    except RuntimeError:
        return

    embed=discord.Embed(description=f"{user_object.mention}'s Avatar", color=0x758cff)
    embed.set_image(url=user_object.avatar_url)
    embed.timestamp = datetime.utcnow()
    await message.channel.send(embed=embed)


async def help_function(message, args, client, stats, cmd_modules, ramfs):
    # Check arguments and such.
    lookup = False

    if len(args) > 0:
        lookup = args[0]

    # Lookup will now either be False or a module lookup.
    # If it's not a lookup, then we just want the category info.

    if lookup == False:
        # We're just doing category info.

        # Initialise embed.
        embed=discord.Embed(title="Category Listing", color=0x00db87)
        embed.set_author(name="Sonnet Help")

        # Start creating module listing.
        for modules in cmd_modules:
            embed.add_field(name=modules.category_info['pretty_name']+ " (" + modules.category_info['name'] + ")", value=modules.category_info['description'], inline=False)
    else:
        # We're looking up a category.

        # Initialise embed.
        embed=discord.Embed(title='Commands in Category "' + args[0].lower() + '"', color=0x00db87)
        embed.set_author(name="Sonnet Help")

        # Start creating command listing.
        cmds = []
        for modules in cmd_modules:
            # Check we're working with the right category.
            if modules.category_info['name'] == args[0].lower():
                # Now we're in the correct category, generate the fields.
                for commands in modules.commands:
                    cmds.append({
                        'pretty_name': modules.commands[commands]['pretty_name'],
                        'description': modules.commands[commands]['description']
                    })

                # We can now break out of this for loop.
                break

        # Load prefix
        PREFIX = load_message_config(message.guild.id, ramfs)["prefix"]

        # Now we generate the actual embed.
        if len(cmds) < 1:
            embed.add_field(name="No commands found in this category.", value="Maybe you misspelled?", inline=False)
        else:
            for info in cmds:
                # Add field.
                embed.add_field(name=PREFIX + info['pretty_name'], value=info['description'], inline=False)

    # Now we have the final embed. Send it.
    await message.channel.send(embed=embed)


category_info = {
    'name': 'utilities',
    'pretty_name': 'Utilities',
    'description': 'Administration commands.'
}


commands = {
    'ping': {
        'pretty_name': 'ping',
        'description': 'Test connection to bot',
        'permission':'everyone',
        'cache':'keep',
        'execute': ping_function
    },
    'profile': {
        'pretty_name': 'profile [user]',
        'description': 'Get a users profile',
        'permission':'everyone',
        'cache':'keep',
        'execute': profile_function
    },
    'help': {
        'pretty_name': 'help [category]',
        'description': 'Print helptext',
        'permission':'everyone',
        'cache':'keep',
        'execute': help_function
    },
    'avatar': {
        'pretty_name': 'avatar [user]',
        'description': 'Get avatar of a user',
        'permission':'everyone',
        'cache':'keep',
        'execute': avatar_function
    }
}
