# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import discord
from datetime import datetime
import time

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
    }
}
