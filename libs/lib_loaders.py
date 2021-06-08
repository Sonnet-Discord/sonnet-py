# cache generation tools
# Ultabear 2020

import importlib

import discord

import random, os, ctypes, time, io, json, pickle, threading

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import sonnet_cfg

importlib.reload(sonnet_cfg)

from lib_db_obfuscator import db_hlapi
from sonnet_cfg import CLIB_LOAD, GLOBAL_PREFIX, BLACKLIST_ACTION

from typing import Dict, List, Union, Any, Tuple, Optional
import lib_lexdpyk_h as lexdpyk


class DotHeaders:

    version = "1.2.3-DEV.0"

    class cdef_load_words:
        argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int]
        restype = ctypes.c_int

    class cdef_load_words_test:
        argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint, ctypes.c_char_p, ctypes.c_int, ctypes.c_int]
        restype = ctypes.c_int

    def __init__(self, lib: ctypes.CDLL):
        self.lib = lib
        for i in filter(lambda i: i.startswith("cdef_"), dir(self)):
            self._wrap(i)

    def _wrap(self, funcname: str) -> None:
        self.lib.__getitem__(funcname[5:]).argtypes = self.__getattribute__(funcname).argtypes
        self.lib.__getitem__(funcname[5:]).restype = self.__getattribute__(funcname).restype


clib_exists = True
clib_name = f"./libs/compiled/sonnet.{DotHeaders.version}.so"
if CLIB_LOAD:
    try:
        loader = DotHeaders(ctypes.CDLL(clib_name)).lib
    except OSError:
        try:
            os.system("make")
            loader = DotHeaders(ctypes.CDLL(clib_name)).lib
        except OSError:
            clib_exists = False
else:
    clib_exists = False


# LCIF system ported for blacklist loader, converted to little endian
def directBinNumber(inData: int, length: int) -> Tuple[int, ...]:
    return tuple(inData.to_bytes(length, byteorder="little"))


defaultcache: Dict[Union[str, int], Any] = {
    "csv": [["word-blacklist", ""], ["filetype-blacklist", ""], ["word-in-word-blacklist", ""], ["antispam", "3,2"], ["char-antispam", "2,2,1000"]],
    "text":
        [
            ["prefix", GLOBAL_PREFIX], ["blacklist-action", BLACKLIST_ACTION], ["blacklist-whitelist", ""], ["regex-notifier-log", ""], ["admin-role", ""], ["moderator-role", ""],
            ["antispam-time", "20"]
            ],
    0: "sonnet_default"
    }


# Read a vnum from a file stream
def read_vnum(fileobj: io.BufferedReader) -> int:
    return int.from_bytes(fileobj.read(int.from_bytes(fileobj.read(1), "little")), "little")


# Write a vnum to a file stream
def write_vnum(fileobj: io.BufferedWriter, number: int) -> None:
    vnum_count = (number.bit_length() + 7) // 8
    fileobj.write(bytes([vnum_count]))
    fileobj.write(bytes(directBinNumber(number, vnum_count)))


# Load config from cache, or load from db if cache isn't existant
def load_message_config(guild_id: int, ramfs: lexdpyk.ram_filesystem, datatypes: Optional[Dict[Union[str, int], Any]] = None) -> Dict[str, Any]:

    datatypes = defaultcache if datatypes is None else datatypes

    for i in ["csv", "text", "json"]:
        if i not in datatypes:
            datatypes[i] = []

    try:

        # Loads fileio object
        blacklist_cache = ramfs.read_f(f"{guild_id}/caches/{datatypes[0]}")
        blacklist_cache.seek(0)
        message_config: Dict[str, Any] = {}

        # Imports csv style data
        for i in datatypes["csv"]:
            csvpre = blacklist_cache.read(read_vnum(blacklist_cache))
            if csvpre:
                message_config[i[0]] = csvpre.decode("utf8").split(",")
            else:
                message_config[i[0]] = i[1].split(",") if i[1] else []

        # Imports text style data
        for i in datatypes["text"]:
            textpre = blacklist_cache.read(read_vnum(blacklist_cache))
            if textpre:
                message_config[i[0]] = textpre.decode("utf8")
            else:
                message_config[i[0]] = i[1]

        # Imports JSON type data
        for i in datatypes["json"]:
            jsonpre = blacklist_cache.read(read_vnum(blacklist_cache))
            if jsonpre:
                message_config[i[0]] = pickle.loads(jsonpre)
            else:
                message_config[i[0]] = i[1]

        return message_config

    except FileNotFoundError:
        message_config = {}

        # Loads base db
        with db_hlapi(guild_id) as db:
            for i in datatypes["csv"] + datatypes["text"] + datatypes["json"]:
                message_config[i[0]] = db.grab_config(i[0])
                if not message_config[i[0]]:
                    message_config[i[0]] = None

        # Load json datatype
        for i in datatypes["json"]:
            if message_config[i[0]]:
                message_config[i[0]] = json.loads(message_config[i[0]])

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
                write_vnum(blacklist_cache, len(outdat))
                blacklist_cache.write(outdat)
            else:
                write_vnum(blacklist_cache, 0)

        # Add text based configs
        for i in datatypes["text"]:
            if message_config[i[0]]:
                outdat = message_config[i[0]].encode("utf8")
                write_vnum(blacklist_cache, len(outdat))
                blacklist_cache.write(outdat)
            else:
                write_vnum(blacklist_cache, 0)

        # Add json configs
        for i in datatypes["json"]:
            if message_config[i[0]]:
                outdat = pickle.dumps(message_config[i[0]])
                write_vnum(blacklist_cache, len(outdat))
                blacklist_cache.write(outdat)
            else:
                write_vnum(blacklist_cache, 0)

        return load_message_config(guild_id, ramfs, datatypes=datatypes)


# Generate an infraction id from the wordlist cache format
def generate_infractionid() -> str:
    if os.path.isfile("datastore/wordlist.cache.db"):
        if clib_exists:
            buf = bytes(256 * 3)
            safe = loader.load_words(b"datastore/wordlist.cache.db\x00", 3, (int(time.time() * 1000000) % (2**32)), buf, len(buf))
            if safe == 0:
                return buf.rstrip(b"\x00").decode("utf8")
            else:
                raise RuntimeError("Wordlist generator received fatal status")
        else:
            with open("datastore/wordlist.cache.db", "rb") as words:
                chunksize = words.read(1)[0]
                num_words = (words.seek(0, io.SEEK_END) - 1) // chunksize
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
            for byte in words.read().split(b"\n"):
                if byte and not len(byte) > 85 and not b"\xc3" in byte:

                    stv = byte.rstrip(b"\r").decode("utf8")
                    byte = (stv[0].upper() + stv[1:].lower()).encode("utf8")

                    structured_data.append(bytes([len(byte)]) + byte)
                    if len(byte) + 1 > maxval:
                        maxval = len(byte) + 1
        with open("datastore/wordlist.cache.db", "wb") as structured_data_file:
            structured_data_file.write(bytes([maxval]))
            for byte in structured_data:
                structured_data_file.write(byte + bytes(maxval - len(byte)))

        return generate_infractionid()


def inc_statistics_better(guild: int, inctype: str, kernel_ramfs: lexdpyk.ram_filesystem) -> None:

    try:
        statistics = kernel_ramfs.read_f(f"{guild}/stats")
    except FileNotFoundError:
        statistics = kernel_ramfs.create_f(f"{guild}/stats", f_type=dict)

    try:
        global_statistics = kernel_ramfs.read_f("global/stats")
    except FileNotFoundError:
        global_statistics = kernel_ramfs.create_f("global/stats", f_type=dict)

    if inctype in statistics:
        statistics[inctype] += 1
    else:
        statistics[inctype] = 1

    if inctype in global_statistics:
        global_statistics[inctype] += 1
    else:
        global_statistics[inctype] = 1


def inc_statistics(indata: List[Any]) -> None:

    guild, inctype, kernel_ramfs = indata

    inc_statistics_better(guild, inctype, kernel_ramfs)


_colortypes_cache: Dict[Any, Any] = {
    0: "sonnet_colortypes",
    "text": [["embed-color-primary", "0x0057e7"], ["embed-color-creation", "0x008744"], ["embed-color-edit", "0xffa700"], ["embed-color-deletion", "0xd62d20"]]
    }


# Why? why would I do this?
# Because variable names can be statically type checked
# I hate bugs more than I hate slow python
class embed_colors:
    primary: str = "primary"
    creation: str = "creation"
    edit: str = "edit"
    deletion: str = "deletion"


def load_embed_color(guild: discord.Guild, colortype: str, ramfs: lexdpyk.ram_filesystem) -> int:
    return int(load_message_config(guild.id, ramfs, datatypes=_colortypes_cache)[f"embed-color-{colortype}"], 16)


# Deprecated immediately as threading.Lock can cause deadlocking in asyncio, what the shit
def get_guild_lock(guild: discord.Guild, ramfs: lexdpyk.ram_filesystem) -> Optional[threading.Lock]:
    return None
