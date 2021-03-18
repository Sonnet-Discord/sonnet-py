# High Level API calls for sonnet style databases
# Ultrabear 2020

import importlib

from sonnet_cfg import DB_TYPE, SQLITE3_LOCATION

# Get db handling library
if DB_TYPE == "mariadb":
    import lib_mdb_handler
    importlib.reload(lib_mdb_handler)
    import json
    from lib_mdb_handler import db_handler, db_error
    with open(".login-info.txt") as login_info_file:  # Grab login data
        db_connection_parameters = json.load(login_info_file)

elif DB_TYPE == "sqlite3":
    import lib_sql_handler
    importlib.reload(lib_sql_handler)
    from lib_sql_handler import db_handler, db_error
    db_connection_parameters = SQLITE3_LOCATION


class DATABASE_FATAL_CONNECTION_LOSS(Exception):
    pass


try:
    db_connection = db_handler(db_connection_parameters)
except db_error.Error:
    print("FATAL: DATABASE CONNECTION ERROR")
    raise DATABASE_FATAL_CONNECTION_LOSS("Database failure")


def db_reconnect():
    global db_connection
    try:
        db_connection.commit()
        return db_connection
    except (db_error.Error, db_error.InterfaceError):
        try:
            db_connection = db_handler(db_connection_parameters)
            return db_connection
        except db_error.Error:
            print("FATAL: DATABASE CONNECTION ERROR")
            raise DATABASE_FATAL_CONNECTION_LOSS("Database failure")


# Because being lazy writes good code
class db_hlapi:
    def __init__(self, guild_id):
        self.database = db_reconnect()
        self.guild = guild_id

    def __enter__(self):
        return self

    def grab_config(self, config):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_config", ["property", config])
        except db_error.OperationalError:
            data = []

        if data:
            return data[0][1]
        else:
            return []

    def add_config(self, config, value):

        try:
            data = self.database.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])
        except db_error.OperationalError:
            self.create_guild_db()
            data = self.database.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])

    # Grab infractions of a user
    def grab_user_infractions(self, userid):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["userID", userid])
        except db_error.OperationalError:
            data = []

        return data

    # grab infractions dealt by a mod
    def grab_moderator_infractions(self, moderatorid):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["moderatorID", moderatorid])
        except db_error.OperationalError:
            data = []

        return data

    # Check if a message is on the starboard already
    def in_starboard(self, message_id):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_starboard", ["messageID", message_id])
        except db_error.OperationalError:
            data = False

        if data:
            return True
        else:
            return False

    def add_to_starboard(self, message_id):

        try:
            self.database.add_to_table(f"{self.guild}_starboard", [["messageID", message_id]])
        except db_error.Error:
            # Raw reaction and nonraw reaction are trying to access the db at the same time
            # I cant think of a better solution
            return False
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_starboard", [["messageID", message_id]])

        return True

    def grab_infraction(self, infractionID):

        try:
            infraction = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["infractionID", infractionID])
        except db_error.OperationalError:
            infraction = None

        if infraction:
            return infraction[0]
        else:
            return False

    def delete_infraction(self, infraction_id):

        try:
            self.database.delete_rows_from_table(f"{self.guild}_infractions", ["infractionID", infraction_id])
        except db_error.OperationalError:
            pass

    def mute_user(self, user, endtime, infractionID):

        try:
            self.database.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])

    def unmute_user(self, **kargs):

        try:
            if "infractionid" in kargs.keys():
                self.database.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", kargs["infractionid"]])
            elif "userid" in kargs.keys():
                self.database.delete_rows_from_table(f"{self.guild}_mutes", ["userid", kargs["userid"]])
        except db_error.OperationalError:
            pass

    def create_guild_db(self):

        self.database.make_new_table(f"{self.guild}_config", [["property", tuple, 1], ["value", str]])
        self.database.make_new_table(f"{self.guild}_infractions", [["infractionID", tuple, 1], ["userID", str], ["moderatorID", str], ["type", str], ["reason", str], ["timestamp", int(64)]])
        self.database.make_new_table(f"{self.guild}_starboard", [["messageID", tuple, 1]])
        self.database.make_new_table(f"{self.guild}_mutes", [["infractionID", tuple, 1], ["userID", str], ["endMute", int(64)]])

    def download_guild_db(self):

        dbdict = {
            "config": [["property", "value"]],
            "infractions": [["infractionID", "userID", "moderatorID", "type", "reason", "timestamp"]],
            "mutes": [["infractionID", "userID", "endMute"]],
            "starboard": [["messageID"]]
            }

        for i in ["config", "infractions", "starboard", "mutes"]:
            try:
                dbdict[i].extend(self.database.fetch_table(f"{self.guild}_{i}"))
            except db_error.OperationalError:
                pass

        return dbdict

    def delete_guild_db(self):

        for i in ["config", "infractions", "starboard", "mutes"]:
            try:
                self.database.delete_table(f"{self.guild}_{i}")
            except db_error.OperationalError:
                pass

    def add_infraction(self, infractionid, userid, moderatorid, infractiontype, reason, timestamp):

        try:
            self.database.add_to_table(
                f"{self.guild}_infractions", [["infractionID", infractionid], ["userID", userid], ["moderatorID", moderatorid], ["type", infractiontype], ["reason", reason], ["timestamp", timestamp]]
                )
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(
                f"{self.guild}_infractions", [["infractionID", infractionid], ["userID", userid], ["moderatorID", moderatorid], ["type", infractiontype], ["reason", reason], ["timestamp", timestamp]]
                )

    def fetch_all_mutes(self):

        # Grab list of tables
        tablelist = self.database.list_tables("%_mutes")

        mutetable = []
        for i in tablelist:
            mutetable.extend([[i[0][:-6]] + list(a) for a in self.database.fetch_table(i[0])])

        return mutetable

    def is_muted(self, **kargs):

        try:
            if "userid" in kargs.keys():
                muted = bool(self.database.fetch_rows_from_table(f"{self.guild}_mutes", ["userID", kargs["userid"]]))
            elif "infractionid" in kargs.keys():
                muted = bool(self.database.fetch_rows_from_table(f"{self.guild}_mutes", ["infractionID", kargs["infractionid"]]))
        except db_error.OperationalError:
            muted = False

        return muted

    def close(self):
        self.database.commit()

    def __exit__(self, err_type, err_value, err_traceback):
        self.database.commit()
        if err_type:
            raise err_type(err_value)
