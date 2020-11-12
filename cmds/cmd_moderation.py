# Moderation commands
# bredo, 2020

import discord


async def kick_user(message, client, stats):
    args = message.content.split()

    # Check that the user running the command has permissions to kick members
    if not message.author.permissions_in(message.channel).kick_members:
        await message.channel.send("Insufficient permissions.")
        return

    # retrieve ID of user to kick.
    id_to_kick = args[1]
    if args[1].startswith("<@") and args[1].endswith(">"):
        id_to_kick = args[1][2:-1]
        if id_to_kick.startswith("!"):
            id_to_kick = id_to_kick[1:]

    # construct string for kick reason
    reason = ""
    if len(args) > 1:
        for i in range(2, len(args)):
            reason = f"{reason} {args[i]}"
    else:
        reason = "sonnet kick"

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

    await message.channel.send(f"Kicked user with ID {id_to_kick}")


commands = {
    'kick': {
        'pretty_name': 'kick',
        'description': 'Kick a user',
        'execute': kick_user
    }
}
