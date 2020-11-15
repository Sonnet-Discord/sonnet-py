# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import discord
from datetime import datetime
import time
import sonnet_cfg

GLOBAL_PREFIX = sonnet_cfg.GLOBAL_PREFIX

def extract_id_from_mention(user_id):
    # Function to extract a user ID from a mention.
    extracted_id = user_id
    if user_id.startswith("<@") and user_id.endswith(">"):
        extracted_id = user_id[2:-1]
        if extracted_id.startswith("!"):
            extracted_id = extracted_id[1:]
    return extracted_id

async def ping_function(message, args, client, stats):
    embed = discord.Embed(title="Pong!", description="Connection between Sonnet and Discord is OK", color=0x00ff6e)
    embed.add_field(name="Process Time", value=str(stats["end"] - stats["start"]) + "ms", inline=False)
    await message.channel.send(embed=embed)

async def profile_function(message, args, client, stats):
    # Get user ID from the message, otherwise use the author's ID.
    try:
        id_to_probe = int(extract_id_from_mention(args[0]))
    except IndexError:
        id_to_probe = message.author.id

    # Get the Member object by user ID, otherwise fail.
    user_object = message.guild.get_member(id_to_probe)
    print(user_object)
    print(id_to_probe)
    # Secondary catch if actually getting the member succeeds but passes nothing to the variable.
    if not user_object:
        await message.channel.send(f"Failed to find user in this guild.")
        return

    # Put here to comply with formatting guidelines.
    created_string = time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime(datetime.timestamp(user_object.created_at)))
    created_string = created_string + " (" + str((datetime.utcnow() - user_object.created_at).days) + " days ago)"

    embed=discord.Embed(title="User Information", description="Cached user information for " + user_object.mention + ":", color=0x758cff)
    embed.set_thumbnail(url=user_object.avatar_url)
    embed.add_field(name="Username", value=user_object.name + "#" + user_object.discriminator, inline=True)
    embed.add_field(name="User ID", value=user_object.id, inline=True)
    embed.add_field(name="Status", value=user_object.raw_status, inline=True)
    embed.add_field(name="Highest Rank", value=user_object.top_role.name, inline=True)
    embed.add_field(name="Created", value=created_string, inline=True)
    embed.timestamp = datetime.now()
    await message.channel.send(embed=embed)

async def help_function(message, args, client, stats, cmd_modules):
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

        # Now we generate the actual embed.
        if len(cmds) < 1:
            embed.add_field(name="No commands found in this category.", value="Maybe you misspelled?", inline=False)
        else:
            for info in cmds:
                # Add field.
                embed.add_field(name=GLOBAL_PREFIX + info['pretty_name'], value=info['description'], inline=False)

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
        'description': 'Ping bot.',
        'execute': ping_function
    },
    'profile': {
        'pretty_name': 'profile',
        'description': 'Profile.',
        'execute': profile_function
    },
    'help': {
        'pretty_name': 'help',
        'description': 'Get help.',
        'execute': help_function
    }
}
