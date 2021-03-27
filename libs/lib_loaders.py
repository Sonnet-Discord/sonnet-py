# cache generation tools
# Ultabear 2020

import importlib

import json, random, os, math, ctypes, time, io
from sonnet_cfg import *

import lib_db_obfuscator
importlib.reload(lib_db_obfuscator)
from lib_db_obfuscator import db_hlapi


class DotHeaders:

    version = "1.2.1-DEV.2"

    class cdef_load_words:
        argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_ulonglong, ctypes.c_char_p, ctypes.c_int]
        restype = ctypes.c_int

    class cdef_load_words_test:
        argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_ulonglong, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        restype = ctypes.c_int

    def __init__(self, lib):
        self.lib = lib
        for i in filter(lambda i: i.startswith("cdef_"), dir(self)):
            self._wrap(i)

    def _wrap(self, funcname):
        self.lib.__getitem__(funcname[5:]).argtypes = self.__getattribute__(funcname).argtypes
        self.lib.__getitem__(funcname[5:]).restype = self.__getattribute__(funcname).restype

try:
    loader = DotHeaders(ctypes.CDLL(f"./libs/compiled/sonnet.{DotHeaders.version}.so")).lib
    clib_exists = True
except OSError:
    clib_exists = False


# LCIF system ported for blacklist loader, converted to little endian
def directBinNumber(inData, length):
    return tuple([(inData >> (8 * i) & 0xff) for i in range(length)])


defaultcache = {
    "csv": [["word-blacklist", ""], ["filetype-blacklist", ""], ["word-in-word-blacklist", ""], ["antispam", "3,2"]],
    "text": [["prefix", GLOBAL_PREFIX], ["blacklist-action", BLACKLIST_ACTION], ["blacklist-whitelist", ""], ["regex-notifier-log", ""], ["admin-role", ""], ["moderator-role", ""]],
    0: "sonnet_default"
    }


# Load config from cache, or load from db if cache isint existant
def load_message_config(guild_id, ramfs, datatypes=defaultcache):
    try:

        # Loads fileio object
        blacklist_cache = ramfs.read_f(f"{guild_id}/caches/{datatypes[0]}")
        blacklist_cache.seek(0)
        message_config = {}

        # Imports csv style data
        for i in datatypes["csv"]:
            message_config[i[0]] = blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little")).decode("utf8")
            if message_config[i[0]]:
                message_config[i[0]] = message_config[i[0]].split(",")
            else:
                message_config[i[0]] = i[1]

        # Imports text style data
        for i in datatypes["text"]:
            preout = blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little"))
            if preout:
                message_config[i[0]] = preout.decode("utf8")
            else:
                message_config[i[0]] = i[1]

        return message_config

    except FileNotFoundError:
        message_config = {}

        # Loads base db
        with db_hlapi(guild_id) as db:
            for i in datatypes["csv"] + datatypes["text"]:
                message_config[i[0]] = db.grab_config(i[0])
                if not message_config[i[0]]:
                    message_config[i[0]] = i[1]

        # Load CSV datatype
        for i in datatypes["csv"]:
            if message_config[i[0]]:
                message_config[i[0]] = message_config[i[0]].lower().split(",")

        # Generate SNOWFLAKE DBCACHE
        blacklist_cache = ramfs.create_f(f"{guild_id}/caches/{datatypes[0]}")
        # Add csv based configs
        for i in datatypes["csv"]:
            if message_config[i[0]]:
                outdat = ",".join(message_config[i[0]]).encode("utf8")
                blacklist_cache.write(bytes(directBinNumber(len(outdat), 2)) + outdat)
            else:
                blacklist_cache.write(bytes(2))

        # Add text based configs
        for i in datatypes["text"]:
            if message_config[i[0]]:
                outdat = message_config[i[0]].encode("utf8")
                blacklist_cache.write(bytes(directBinNumber(len(outdat), 2)) + outdat)
            else:
                blacklist_cache.write(bytes(2))

        return message_config


def generate_infractionid():
    if os.path.isfile("datastore/wordlist.cache.db"):
        if clib_exists:
            buf = bytes(256 * 3)
            safe = loader.load_words(b"datastore/wordlist.cache.db\x00", 3, int(time.time() * 1000000), buf, len(buf))
            if safe == 0:
                return buf.rstrip(b"\x00").decode("utf8")
            else:
                raise RuntimeError("Wordlist generator recieved fatal status")
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

                    i = i.rstrip(b"\r").decode("utf8")
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
