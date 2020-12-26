# Parsers for message handling
# Ultrabear 2020

import re
from sonnet_cfg import DB_TYPE

from lib_db_obfuscator import db_hlapi


def parse_blacklist(message, blacklist):
    # Preset values
    broke_blacklist = False
    infraction_type = []

    # Check message agaist word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in message.content.lower().replace("\n"," ").split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append("Word")

    # Check message agaist word in word blacklist
    word_blacklist = blacklist["word-in-word-blacklist"]
    if word_blacklist:
        for i in word_blacklist:
            if i in message.content.lower():
                broke_blacklist = True
                infraction_type.append("WordInWord")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        if re.findall(i, message.content.lower()):
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

    if blacklist["blacklist-whitelist"] and int(blacklist["blacklist-whitelist"]) in [i.id for i in message.author.roles]:
        broke_blacklist = False

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
    with db_hlapi(message.guild.id) as db:
        db.add_config(log_name, log_channel)

    await message.channel.send(f"Successfully updated {log_name}")

async def parse_permissions(message, perms):

    you_shall_pass = False
    if perms == "everyone":
        you_shall_pass =  True
    elif perms == "moderator":
        you_shall_pass = message.author.permissions_in(message.channel).ban_members
    elif perms == "administrator":
        you_shall_pass = message.author.permissions_in(message.channel).administrator
    elif perms == "owner":
        you_shall_pass = message.author.id == message.channel.guild.owner.id

    if you_shall_pass:
        return True
    else:
        await message.channel.send(f"You need permission group {perms} to run this command")
        return False
