# Parsers for message handling
# Ultrabear 2020

import re
from lib_mdb_handler import db_handler, db_error

def parse_blacklist(message, blacklist):
    # Preset values
    broke_blacklist = False
    infraction_type = []

    # Check message agaist word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in message.content.lower().split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append("Word")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        if re.findall(i, message.content):
            broke_blacklist = True
            infraction_type.append("RegEx")

    # Check against filetype blacklist
    filetype_blacklist = blacklist["filetype-blacklist"]
    if filetype_blacklist and message.attachments:
        for i in message.attachments:
            for a in filetype_blacklist:
                if i.filename.lower().endswith(a):
                    broke_blacklist = True
                    infraction_type.append("FileType")

    return (broke_blacklist, infraction_type)


# Parse if we skip a message due to X reasons
def parse_skip_message(Client, message):

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return True

    # Ignore message if author is a bot
    if message.author.bot:
        return True

    return False


# Parse a boolean datatype from a string
def parse_boolean(instr):

    yeslist = ["yes","true","y","t"]
    nolist = ["no","false","n","f"]

    if instr.lower() in yeslist:
        return True
    elif instr.lower() in nolist:
        return False

    return 0


# Put channel item in DB, and check for collisions
async def update_log_channel(message, args, client, log_name):

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        raise RuntimeError("Insufficient permissions.")

    if len(args) >= 1:
        log_channel = args[0].strip("<#!>")
    else:
        await message.channel.send("No Channel supplied")
        raise RuntimeError("No Channel supplied")

    try:
        log_channel = int(log_channel)
    except ValueError:
        await message.channel.send("Channel is not a valid channel")
        raise RuntimeError("Channel is not a valid channel")

    discord_channel = client.get_channel(log_channel)
    if not discord_channel:
        await message.channel.send("Channel is not a valid channel")
        raise RuntimeError("Channel is not a valid channel")

    if discord_channel.guild.id != message.channel.guild.id:
        await message.channel.send("Channel is not in guild")
        raise RuntimeError("Channel is not in guild")

    # Nothing failed so send to db
    with db_handler() as db:
        db.add_to_table(f"{message.guild.id}_config", [
            ["property", log_name],
            ["value", log_channel]
            ])

    await message.channel.send(f"Successfully updated {log_name}")
