# Parsers for message handling
# Ultrabear 2020

import importlib

import re2 as re
from sonnet_cfg import DB_TYPE
import lz4.frame, io, discord, os

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
import lib_encryption_wrapper
importlib.reload(lib_encryption_wrapper)

from lib_db_obfuscator import db_hlapi
from lib_encryption_wrapper import encrypted_reader


def parse_blacklist(indata):
    message, blacklist = indata

    # Preset values
    broke_blacklist = False
    infraction_type = []

    # If in whitelist, skip parse to save resources
    if blacklist["blacklist-whitelist"] and int(blacklist["blacklist-whitelist"]) in [i.id for i in message.author.roles]:
        return [False, []]

    text_to_blacklist = re.sub(r'[^a-z0-9 ]+', '', message.content.lower().replace(":", " ").replace("\n", " "))

    # Check message agaist word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in text_to_blacklist.split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append("Word")

    # Check message agaist word in word blacklist
    word_blacklist = blacklist["word-in-word-blacklist"]
    if word_blacklist:
        for i in word_blacklist:
            if i in text_to_blacklist.replace(" ", ""):
                broke_blacklist = True
                infraction_type.append("WordInWord")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        try:
            if re.findall(i, message.content.lower()):
                broke_blacklist = True
                infraction_type.append("RegEx")
        except re.error:
            pass  # GC for old regex

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

    # Ignore dmmessage
    if not message.guild:
        return True

    return False


# Parse a boolean datatype from a string
def parse_boolean(instr):

    yeslist = ["yes", "true", "y", "t", "1"]
    nolist = ["no", "false", "n", "f", "0"]

    if instr.lower() in yeslist:
        return True
    elif instr.lower() in nolist:
        return False

    return 0


# Put channel item in DB, and check for collisions
async def update_log_channel(message, args, client, log_name):

    if args:
        log_channel = args[0].strip("<#!>")
    else:
        with db_hlapi(message.guild.id) as db:
            log_channel = db.grab_config(log_name) or "nothing"
        await message.channel.send(f"{log_name} is set to {log_channel}")
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
        you_shall_pass = True
    elif perms == "moderator":
        you_shall_pass = message.author.permissions_in(message.channel).ban_members
    elif perms == "administrator":
        you_shall_pass = message.author.permissions_in(message.channel).administrator
    elif perms == "owner":
        you_shall_pass = message.author.id == message.channel.guild.owner.id

    if you_shall_pass:
        return True
    else:
        await message.channel.send(f"You need permissions `{perms}` to run this command")
        return False


def ifgate(inlist):
    for i in inlist:
        if i:
            return True
    return False


def grab_files(guild_id, message_id, ramfs, delete=False):

    try:

        files = ramfs.ls(f"files/{guild_id}/{message_id}")[1]
        discord_files = []
        for i in files:

            loc = ramfs.read_f(f"files/{guild_id}/{message_id}/{i}/pointer")
            loc.seek(0)
            pointer = loc.read()

            keys = ramfs.read_f(f"files/{guild_id}/{message_id}/{i}/key")
            keys.seek(0)
            key = keys.read(32)
            iv = keys.read(16)

            encrypted_file = encrypted_reader(pointer, key, iv)
            rawfile = io.BytesIO()
            rawfile.write(lz4.frame.decompress(encrypted_file.read()))
            rawfile.seek(0)
            discord_files.append(discord.File(rawfile, filename=i))
            if delete:
                os.remove(pointer)

        if delete:
            ramfs.rmdir(f"files/{guild_id}/{message_id}")

        return discord_files

    except FileNotFoundError:

        return None
