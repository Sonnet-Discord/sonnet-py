# Moderation commands
# bredo, 2020

import discord, sqlite3, datetime, time, random


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


async def log_infraction(message, client, user_id, infraction_reason, infraction_type):
    generated_id = gen_infraction_id(infraction_type)
    query = "SELECT * FROM config WHERE property = 'infraction-log'"
    query_two = "INSERT INTO infractions (infractionID, userID, moderatorID, type, reason, timestamp) VALUES(?, ?, ?, ?, ?, ?)"
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    cur_two = con.cursor()
    try:
        cur.execute(query)
    except sqlite3.OperationalError:
        await message.channel.send("ERROR: No guild database. Run recreate-db to fix.")
        return
    except TypeError:
        await message.channel.send("ERROR: Please specify a channel for infraction logs using infraction-log")
        return

    try:
        log_channel = client.get_channel(int(cur.fetchone()[1]))
    except TypeError:
        await message.channel.send("ERROR: Please specify a channel for infraction logs using infraction-log")
        return

    try:
        cur_two.execute(query_two, (generated_id, user_id, message.author.id, infraction_type, infraction_reason, round(time.time())))
    except TypeError:
        await message.channel.send("ERROR: Failed to add infraction to database.")
        return

    con.commit()
    con.close()

    user = client.get_user(int(user_id))

    embed = discord.Embed(title="Sonnet", description=f"New infraction for <@{user_id}>:", color=0x758cff)
    # embed.set_thumbnail(url="") TODO: avatar thing it's 2am i can't be bothered
    embed.add_field(name="Infraction ID", value=generated_id)
    embed.add_field(name="Moderator", value=f"{message.author.name}#{message.author.discriminator}")
    embed.add_field(name="User", value=f"{user.name}#{user.discriminator}")
    embed.add_field(name="Type", value=infraction_type)
    embed.add_field(name="Reason", value=infraction_reason)

    dm_embed = discord.Embed(title="Sonnet", description=f"Your punishment in {message.guild.name} has been updated:", color=0x758cff)
    # embed.set_thumbnail(url="") TODO: avatar thing it's 2am i can't be bothered
    dm_embed.add_field(name="Infraction ID", value=generated_id)
    dm_embed.add_field(name="Type", value=infraction_type)
    dm_embed.add_field(name="Reason", value=infraction_reason)
    await log_channel.send(embed=embed)
    await user.send(embed=dm_embed)


async def kick_user(message, args, client, stats, cmds):
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
    await log_infraction(message, client, id_to_kick, reason, "kick")

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
    await log_infraction(message, client, id_to_ban, reason, "ban")


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
