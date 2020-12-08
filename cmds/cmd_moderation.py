# Moderation commands
# bredo, 2020

import discord, datetime, time, random

from lib_mdb_handler import db_handler, db_error

def extract_id_from_mention(user_id):
    # Function to extract a user ID from a mention.
    extracted_id = user_id
    if user_id.startswith("<@") and user_id.endswith(">"):
        extracted_id = user_id[2:-1]
        if extracted_id.startswith("!"):
            extracted_id = extracted_id[1:]
    return extracted_id


def gen_infraction_id(infraction_type):
    # Type is based on binary. Truth table below:
    # Warn: 0001
    # Kick: 0010
    # Ban: 0011
    # Mute: 0100

    inf_type = 0

    if infraction_type == "warn":
        inf_type = '0001'
    elif infraction_type == "kick":
        inf_type = '0010'
    elif infraction_type == "ban":
        inf_type = '0011'
    elif infraction_type == "mute":
        inf_type = '0100'

    # Now generate the timestamp.
    current_time = int(round(time.time()))

    # Convert type and time to binary.
    current_time = bin(current_time)[2:]

    # Now with both converted to binary, concatenate.
    inf_id = str(current_time) + str(inf_type) + bin(random.randint(0,9999))[2:]

    # Finally, convert back to denary.
    inf_id = int(inf_id, 2)

    return inf_id


def dec_to_bin(num):
    if num > 1:
        dec_to_bin(num // 2)

    return num % 2


async def log_infraction(message, client, user_id, moderator_id, infraction_reason, infraction_type):
    generated_id = gen_infraction_id(infraction_type)
    database = db_handler()
    
    # Grab log channel id from db
    try:
        channel_id = database.fetch_rows_from_table(f"{message.guild.id}_config", ["property", "infraction-log"])[0][1]
    except db_error.OperationalError:
        await message.channel.send("ERROR: No guild database. Run recreate-db to fix.")
        database.close()
        return
    except TypeError:
        await message.channel.send("ERROR: Please specify a channel for infraction logs using infraction-log")
        database.close()
        return
    except IndexError:
        await message.channel.send("ERROR: Please specify a channel for infraction logs using infraction-log")
        database.close()
        return
    
    # Generate log channel object
    try:
        log_channel = client.get_channel(int(channel_id))
    except TypeError:
        await message.channel.send("ERROR: Please specify a channel for infraction logs using infraction-log")
        database.close()
        return

    
    # Send infraction to database
    try:
        database.add_to_table(f"{message.guild.id}_infractions", [
            ["infractionID", generated_id],
            ["userID", user_id],
            ["moderatorID", moderator_id],
            ["type", infraction_type],
            ["reason", infraction_reason],
            ["timestamp", round(time.time())]
            ])
    except TypeError:
        await message.channel.send("ERROR: Failed to add infraction to database.")
        database.close()
        return

    database.close()

    user = client.get_user(int(user_id))

    embed = discord.Embed(title="Sonnet", description=f"New infraction for <@{user_id}>:", color=0x758cff)
    # embed.set_thumbnail(url="") TODO: avatar thing it's 2am i can't be bothered
    embed.add_field(name="Infraction ID", value=str(generated_id))
    embed.add_field(name="Moderator", value=f"{client.get_user(int(moderator_id))}")
    embed.add_field(name="User", value=f"{user}")
    embed.add_field(name="Type", value=infraction_type)
    embed.add_field(name="Reason", value=infraction_reason)

    dm_embed = discord.Embed(title="Sonnet", description=f"Your punishment in {message.guild.name} has been updated:",
                             color=0x758cff)
    # embed.set_thumbnail(url="") TODO: avatar thing it's 2am i can't be bothered
    dm_embed.add_field(name="Infraction ID", value=str(generated_id))
    dm_embed.add_field(name="Type", value=infraction_type)
    dm_embed.add_field(name="Reason", value=infraction_reason)
    await log_channel.send(embed=embed)
    await user.send(embed=dm_embed)


async def warn_user(message, args, client, stats, cmds):

    automod = False
    try:
        if (type(args[0]) == int):
            args[0] = str(args[0])
            automod = True
    except IndexError:
        pass
    
    # Check that the user running the command has permissions to kick members
    if not(message.author.permissions_in(message.channel).kick_members) and not(automod):
            await message.channel.send("Insufficient permissions.")
            return
    
    # If automod then moderator id is the bots id
    if automod:
        moderator_id = client.user.id
    else:
        moderator_id = message.author.id
    
    # construct string for warn reason
    if len(args) > 0:
        reason = " ".join(args[1:])
    else:
        reason = "Sonnet Warn"

    # Extract user ID from arguments, error if this is not provided.
    try:
        id_to_warn = extract_id_from_mention(args[0])
    except IndexError:
        await message.channel.send("ERROR: No User ID provided.")
        return

    # this serves no purpose but to yell at you
    try:
        does_this_person_actually_exist = client.get_user(int(id_to_warn))
    except ValueError:
        await message.channel.send("ERROR: Invalid ID")
        return

    try:
        does_this_person_actually_exist.name
    except AttributeError:
        await message.channel.send("ERROR: Invalid User")
        return

    # Attempt to kick the user - excepts on some errors.
    await log_infraction(message, client, id_to_warn, moderator_id, reason, "warn")
    
    if not automod:
        await message.channel.send(f"Warned user with ID {id_to_warn} for {reason}")


async def kick_user(message, args, client, stats, cmds):
    args = message.content.split()

    # Check that the user running the command has permissions to kick members
    if not message.author.permissions_in(message.channel).kick_members:
        await message.channel.send("Insufficient permissions.")
        return

    # construct string for kick reason
    if len(args) > 1:
        reason = " ".join(args[1:])
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
    await log_infraction(message, client, id_to_kick, message.author.id, reason, "kick")

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


async def ban_user(message, args, client, stats, cmds):
    args = message.content.split()

    # Check if message author has ban permissions in the current guild.
    if not message.author.permissions_in(message.channel).ban_members:
        await message.channel.send("Insufficient permissions.")
        return

    # Construct reason string
    if len(args) > 1:
        reason = " ".join(args[1:])
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
    await log_infraction(message, client, id_to_ban, message.author.id, reason, "ban")


category_info = {
    'name': 'moderation',
    'pretty_name': 'Moderation',
    'description': 'Moderation commands.'
}


commands = {
    'warn': {
        'pretty_name': 'warn',
        'description': 'Warn a user',
        'execute': warn_user
    },
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
