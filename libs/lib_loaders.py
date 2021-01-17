# cache generation tools
# Ultabear 2020

import importlib

import json, random, os, math
from sonnet_cfg import *

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
from lib_db_obfuscator import db_hlapi


# LCIF system ported for blacklist loader, converted to little endian
def directBinNumber(inData, length):
    return tuple([(inData >> (8 * i) & 0xff) for i in range(length)])


# Load config from cache, or load from db if cache isint existant
def load_message_config(guild_id, ramfs):
    datatypes = {
        "csv": ["word-blacklist", "filetype-blacklist", "word-in-word-blacklist", "antispam"],
        "text": ["prefix", "blacklist-action", "starboard-emoji", "starboard-enabled", "starboard-count", "blacklist-whitelist"],
        "list": ["regex-blacklist"]
        }
    try:

        # Loads fileio object
        blacklist_cache = ramfs.read_f(f"datastore/{guild_id}.cache.db")
        blacklist_cache.seek(0)
        message_config = {}

        # Imports csv style data
        for i in datatypes["csv"]:
            message_config[i] = blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little")).decode("utf8")
            if message_config[i]:
                message_config[i] = message_config[i].split(",")
            else:
                message_config[i] = []

        # Imports text style data
        for i in datatypes["text"]:
            preout = blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little"))
            if preout:
                message_config[i] = preout.decode("utf8")
            else:
                message_config[i] = ""

        # Imports list style data
        for lists in datatypes["list"]:
            prelist = []
            for i in range(int.from_bytes(blacklist_cache.read(2), "little")):
                prelist.append(blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little")).decode("utf8"))
            message_config[lists] = prelist

        return message_config

    except FileNotFoundError:
        db = db_hlapi(guild_id)
        message_config = {}

        # Loads base db
        for i in datatypes["csv"] + datatypes["text"] + datatypes["list"]:
            message_config[i] = db.grab_config(i)
        db.close()

        # Loads regex
        if message_config["regex-blacklist"]:
            message_config["regex-blacklist"] = [i.split(" ")[1][1:-2] for i in json.loads(message_config["regex-blacklist"])["blacklist"]]
        else:
            message_config["regex-blacklist"] = []

        # Loads word, filetype blacklist
        for i in datatypes["csv"]:
            if message_config[i]:
                message_config[i] = message_config[i].lower().split(",")

        # Generate various defaults
        if not message_config["prefix"]:
            message_config["prefix"] = GLOBAL_PREFIX

        if not message_config["blacklist-action"]:
            message_config["blacklist-action"] = BLACKLIST_ACTION

        if not message_config["starboard-emoji"]:
            message_config["starboard-emoji"] = STARBOARD_EMOJI

        if not message_config["starboard-enabled"]:
            message_config["starboard-enabled"] = "0"

        if not message_config["starboard-count"]:
            message_config["starboard-count"] = STARBOARD_COUNT

        if not message_config["antispam"]:
            message_config["antispam"] = ["3", "2"]

        # Generate SNOWFLAKE DBCACHE
        blacklist_cache = ramfs.create_f(f"datastore/{guild_id}.cache.db")
        # Add csv based configs
        for i in datatypes["csv"]:
            if message_config[i]:
                outdat = ",".join(message_config[i]).encode("utf8")
                blacklist_cache.write(bytes(directBinNumber(len(outdat), 2)) + outdat)
            else:
                blacklist_cache.write(bytes(2))

        # Add text based configs
        for i in datatypes["text"]:
            if message_config[i]:
                outdat = message_config[i].encode("utf8")
                blacklist_cache.write(bytes(directBinNumber(len(outdat), 2)) + outdat)
            else:
                blacklist_cache.write(bytes(2))

        # Add list based configs
        for i in datatypes["list"]:
            if message_config[i]:
                preout = b""
                for regex in message_config[i]:
                    preout += bytes(directBinNumber(len(regex.encode("utf8")), 2)) + regex.encode("utf8")
                blacklist_cache.write(bytes(directBinNumber(len(message_config[i]), 2)) + preout)
            else:
                blacklist_cache.write(bytes(2))

        return message_config


def generate_infractionid():
    try:
        num_words = os.path.getsize("datastore/wordlist.cache.db") - 1
        with open("datastore/wordlist.cache.db", "rb") as words:
            chunksize = int.from_bytes(words.read(1), "big")
            num_words /= chunksize
            values = ([random.randint(0, (num_words - 1)) for i in range(3)])
            output = ""
            for i in values:
                words.seek(i * chunksize + 1)
                preout = (words.read(int.from_bytes(words.read(1), "big"))).decode("utf8")
                output += preout[0].upper() + preout[1:]
        return output

    except FileNotFoundError:
        with open("common/wordlist.txt", "r") as words:
            maxval = 0
            structured_data = []
            for i in words.read().encode("utf8").split(b"\n"):
                if i:
                    structured_data.append(bytes([len(i)]) + i)
                    if len(i) + 1 > maxval:
                        maxval = len(i) + 1
        with open("datastore/wordlist.cache.db", "wb") as structured_data_file:
            structured_data_file.write(bytes([maxval]))
            for i in structured_data:
                structured_data_file.write(i + bytes(maxval - len(i)))

        return generate_infractionid()


def read_vnum(fileobj):
    return int.from_bytes(fileobj.read(int.from_bytes(fileobj.read(1), "little")), "little")


def write_vnum(fileobj, number):
    vnum_count = math.ceil((len(bin(number)) - 2) / 8)
    fileobj.write(bytes([vnum_count]))
    fileobj.write(bytes(directBinNumber(number, vnum_count)))


def inc_statistics(indata):

    guild, inctype, kernel_ramfs = indata

    stats_of = ["on-message", "on-message-edit", "on-message-delete", "on-reaction-add", "on-raw-reaction-add"]

    try:
        statistics_file = kernel_ramfs.read_f(f"persistent/{guild}/stats")
        statistics_file.seek(0)
    except FileNotFoundError:
        statistics_file = kernel_ramfs.create_f(f"persistent/{guild}/stats")
        statistics_file.write(bytes(len(stats_of)))
        statistics_file.seek(0)

    try:
        global_statistics_file = kernel_ramfs.read_f(f"persistent/global/stats")
        global_statistics_file.seek(0)
    except FileNotFoundError:
        global_statistics_file = kernel_ramfs.create_f(f"persistent/global/stats")
        global_statistics_file.write(bytes(len(stats_of)))
        global_statistics_file.seek(0)

    # Read vnum and write to dict
    datamap = {}
    global_datamap = {}
    for i in stats_of:
        datamap[i] = read_vnum(statistics_file)
        global_datamap[i] = read_vnum(global_statistics_file)

    datamap[inctype] += 1
    global_datamap[inctype] += 1

    statistics_file.seek(0)
    global_statistics_file.seek(0)
    for i in stats_of:
        write_vnum(statistics_file, datamap[i])
        write_vnum(global_statistics_file, global_datamap[i])

    statistics_file.truncate()
    global_statistics_file.truncate()
