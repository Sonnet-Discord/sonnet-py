# cache generation tools
# Ultabear 2020

import importlib

import json, random, os, math, ctypes, time, io
from sonnet_cfg import *

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
from lib_db_obfuscator import db_hlapi

try:
    loader = ctypes.CDLL("./libs/compiled/sonnet.1.1.4-DEV.1.so")
    loader.load_words.argtypes = [ctypes.c_int, ctypes.c_ulonglong, ctypes.c_char_p]
    loader.load_words.restype = ctypes.c_void_p
    clib_exists = True
except OSError:
    clib_exists = False


# LCIF system ported for blacklist loader, converted to little endian
def directBinNumber(inData, length):
    return tuple([(inData >> (8 * i) & 0xff) for i in range(length)])


# Load config from cache, or load from db if cache isint existant
def load_message_config(guild_id, ramfs):
    datatypes = {
        "csv": ["word-blacklist", "filetype-blacklist", "word-in-word-blacklist", "antispam"],
        "text": ["prefix", "blacklist-action", "starboard-emoji", "starboard-enabled", "starboard-count", "blacklist-whitelist", "regex-notifier-log", "admin-role", "moderator-role"],
        "list": []
        }
    try:

        # Loads fileio object
        blacklist_cache = ramfs.read_f(f"{guild_id}/cache")
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
        message_config = {}

        # Loads base db
        with db_hlapi(guild_id) as db:
            for i in datatypes["csv"] + datatypes["text"] + datatypes["list"]:
                message_config[i] = db.grab_config(i)

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
        blacklist_cache = ramfs.create_f(f"{guild_id}/cache")
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
    if os.path.isfile("datastore/wordlist.cache.db"):
        if clib_exists:
            buf = bytes(256 * 3)
            loader.load_words(3, int(time.time() * 1000000), buf)
            return buf.rstrip(b"\x00").decode("utf8")
        else:
            with open("datastore/wordlist.cache.db", "rb") as words:
                chunksize = words.read(1)[0]
                num_words = (words.seek(0, io.SEEK_END) - 1) / chunksize
                values = ([random.randint(0, (num_words - 1)) for i in range(3)])
                output = []
                for i in values:
                    words.seek(i * chunksize + 1)
                    output.append((words.read(words.read(1)[0])).decode("utf8"))

            return "".join(output)

    else:
        with open("common/wordlist.txt", "rb") as words:
            maxval = 0
            structured_data = []
            for i in words.read().split(b"\n"):
                if i and not len(i) > 85 and not b"\xc3" in i:

                    i = i.decode("utf8")
                    i = (i[0].upper() + i[1:].lower()).encode("utf8")

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

    try:
        statistics = kernel_ramfs.read_f(f"{guild}/stats")
    except FileNotFoundError:
        statistics = kernel_ramfs.create_f(f"{guild}/stats", f_type=dict)

    try:
        global_statistics = kernel_ramfs.read_f(f"global/stats")
    except FileNotFoundError:
        global_statistics = kernel_ramfs.create_f(f"global/stats", f_type=dict)

    if inctype in statistics:
        statistics[inctype] += 1
    else:
        statistics[inctype] = 1

    if inctype in global_statistics:
        global_statistics[inctype] += 1
    else:
        global_statistics[inctype] = 1
