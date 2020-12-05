# Blacklist cache generation tool
# Ultabear 2020

from lib_sql_handler import db_handler, db_error
import json

# Load blacklist from cache, or load from db if cache isint existant
def load_blacklist(guild_id):
    try:
        with open(f"datastore/{guild_id}.cache.db", "r") as blacklist_cache:
            return json.load(blacklist_cache)
    except FileNotFoundError:
        db = db_handler(f"datastore/{guild_id}.db")
        blacklist = {}

        # Loads base db
        for i in ["word-blacklist","regex-blacklist","filetype-blacklist"]:
            try:
                blacklist[i] = db.fetch_rows_from_table("config", ["property",i])[0][1]
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

        with open(f"datastore/{guild_id}.cache.db", "w") as blacklist_cache:
            json.dump(blacklist, blacklist_cache)
        return blacklist
