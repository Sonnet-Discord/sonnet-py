import sys, gzip, json, os

sys.path.insert(1, os.getcwd() + "/libs")
sys.path.insert(1, os.getcwd() + "/common")

from lib_db_obfuscator import db_hlapi

with gzip.open(sys.argv[1], "rb") as fname:

    dbdict = json.loads(fname.read())

with db_hlapi(sys.argv[2]) as db:
    if not db.upload_guild_db(dbdict):
        print("gztodb failed on db upload")
