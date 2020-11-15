# Moderation commands
# bredo, 2020

import discord, sqlite3


def extract_id_from_mention(user_id):
    # Function to extract a user ID from a mention.
    extracted_id = user_id
    if user_id.startswith("<@") and user_id.endswith(">"):
        extracted_id = user_id[2:-1]
        if extracted_id.startswith("!"):
            extracted_id = extracted_id[1:]
    return extracted_id


async def kick_user(message, args, client, stats):
    args = message.content.split()

    # Check that the user running the command has permissions to kick members
    if not message.author.permissions_in(message.channel).kick_members:
        await message.channel.send("Insufficient permissions.")
        return

    # construct string for kick reason
    reason = ""
    if len(args) > 1:
        for i in range(2, len(args)):
            reason = f"{reason} {args[i]}"
    else:
        reason = "Sonnet Kick"

    # Extract user ID from arguments, error if this is not provided.
    try:
        id_to_kick = extract_id_from_mention(args[1])
    except IndexError:
        await message.channel.send("ERROR: No User ID provided.")
        return

    # make it so people can't kick themself
    if str(message.author.id) == id_to_kick:
        await message.channel.send("ERROR: You can't kick yourself. Stop trying :)")
        return

    # Attempt to kick the user - excepts on some errors.
    try:
        await message.guild.kick(client.get_user(int(id_to_kick)), reason=reason)
    except AttributeError:
        await message.channel.send("ERROR: Invalid User.")
        return
    except ValueError:
        await message.channel.send("ERROR: Not an ID.")
        return
    except discord.errors.Forbidden:
        await message.channel.send("ERROR: The bot does not have permission to kick this user.")
        return

    await message.channel.send(f"Kicked user with ID {id_to_kick} for {reason}")


async def ban_user(message, args, client, stats):
    args = message.content.split()

    # Check if message author has ban permissions in the current guild.
    if not message.author.permissions_in(message.channel).ban_members:
        await message.channel.send("Insufficient permissions.")
        return

    # Construct reason string
    reason = ""
    if len(args) > 1:
        for i in range(2, len(args)):
            reason = f"{reason} {args[i]}"
    else:
        reason = "Sonnet Ban"

    # Extract User ID from arguments, handle error if it doesn't exist
    try:
        id_to_ban = extract_id_from_mention(args[1])
    except IndexError:
        await message.channel.send("ERROR: No User ID provided.")
        return

    # Makes it so people can't ban themselves
    if str(message.author.id) == id_to_ban:
        await message.channel.send("ERROR: You can't ban yourself. Stop trying :)")
        return

    # Attempts to ban the user
    try:
        await message.guild.ban(client.get_user(int(id_to_ban)), reason=reason, delete_message_days=0)
    except AttributeError:
        await message.channel.send("ERROR: Invalid User.")
        return
    except ValueError:
        await message.channel.send("ERROR: Not an ID")
        return
    except discord.errors.Forbidden:
        await message.channel.send("ERROR: The bot does not have permission to ban this user.")
        return

    await message.channel.send(f"Banned user with ID {id_to_ban} for {reason}")

category_info = {
    'name': 'moderation',
    'pretty_name': 'Moderation',
    'description': 'Moderation commands.'
}

commands = {
    'kick': {
        'pretty_name': 'kick',
        'description': 'Kick a user',
        'execute': kick_user
    },
    'ban': {
        'pretty_name': 'ban',
        'description': 'Ban a user',
        'execute': ban_user
    }
}
