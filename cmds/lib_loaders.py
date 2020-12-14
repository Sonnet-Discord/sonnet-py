# cache generation tools
# Ultabear 2020

from cmds.lib_mdb_handler import db_handler, db_error
import json, random, os, math


# LCIF system ported for blacklist loader, converted to little endian
def directBinNumber(inData,length):
    return tuple([(inData >> (8*i) & 0xff ) for i in range(length)])


# Load blacklist from cache, or load from db if cache isint existant
def load_blacklist(guild_id):
    try:
        with open(f"datastore/{guild_id}.cache.db", "rb") as blacklist_cache:
            blacklist = {}
            for i in ["word-blacklist","filetype-blacklist"]:
                blacklist[i] = blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little")).decode("utf8")
                if blacklist[i]:
                    blacklist[i] = blacklist[i].split(",")
                else:
                    blacklist[i] = []
            for regex in ["regex-blacklist"]:
                prelist = []
                for i in range(int.from_bytes(blacklist_cache.read(2), "little")):
                    prelist.append(blacklist_cache.read(int.from_bytes(blacklist_cache.read(2), "little")).decode("utf8"))
                blacklist[regex] = prelist

        return blacklist

    except FileNotFoundError:
        db = db_handler()
        blacklist = {}

        # Loads base db
        for i in ["word-blacklist","regex-blacklist","filetype-blacklist"]:
            try:
                blacklist[i] = db.fetch_rows_from_table(f"{guild_id}_config", ["property",i])[0][1]
            except db_error.OperationalError:
                blacklist[i] = []
            except IndexError:
                blacklist[i] = []
        db.close()

        # Loads regex
        if blacklist["regex-blacklist"]:
            blacklist["regex-blacklist"] = [i.split(" ")[1][1:-2] for i in json.loads(blacklist["regex-blacklist"])["blacklist"]]
        else:
            blacklist["regex-blacklist"] = []

        # Loads word, filetype blacklist
        for i in ["word-blacklist","filetype-blacklist"]:
            if blacklist[i]:
                blacklist[i] = blacklist[i].lower().split(",")

        # Generate SNOWFLAKE DBCACHE
        with open(f"datastore/{guild_id}.cache.db", "wb") as blacklist_cache:
            # ORDER : word blacklist, filetype blacklist, regex blacklist
            for i in ["word-blacklist","filetype-blacklist"]:
                if blacklist[i]:
                    outdat = ",".join(blacklist[i])
                    blacklist_cache.write(bytes(directBinNumber(len(outdat),2))+outdat.encode("utf8"))
                else:
                    blacklist_cache.write(bytes(2))

            # Serialize regex blacklist
            for i in ["regex-blacklist"]:
                if blacklist[i]:
                    preout = b""
                    for regex in blacklist[i]:
                        preout += bytes(directBinNumber(len(regex),2))+regex.encode("utf8")
                    blacklist_cache.write(bytes(directBinNumber(len(blacklist[i]),2))+preout)
                else:
                    blacklist_cache.write(bytes(2))

        return blacklist


def generate_infractionid():
    try:
        num_words = os.path.getsize("datastore/wordlist.cache.db")-1
        with open("datastore/wordlist.cache.db","rb") as words:
            chunksize = int.from_bytes(words.read(1), "big")
            num_words /= chunksize
            values  = sorted([random.randint(0,(num_words-1)) for i in range(3)])
            output = ""
            for i in values:
                words.seek(i*chunksize+1)
                preout = (words.read(int.from_bytes(words.read(1), "big"))).decode("utf8")
                output += preout[0].upper()+preout[1:]
        return output

    except FileNotFoundError:
        with open("common/wordlist.txt", "r") as words:
            maxval = 0
            structured_data = []
            for i in words.read().split("\n"):
                structured_data.append(bytes([len(i)])+i.encode("utf8"))
                if len(i)+1 > maxval:
                    maxval = len(i)+1
        with open("datastore/wordlist.cache.db","wb") as structured_data_file:
            structured_data_file.write(bytes([maxval]))
            for i in structured_data:
                structured_data_file.write(i+bytes(maxval-len(i)))
        return generate_infractionid()
