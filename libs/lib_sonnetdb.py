# High Level API calls for sonnet style databases
# Ultrabear 2020

from sonnet_cfg import DB_TYPE, SQLITE3_LOCATION

# Get db handling library
if DB_TYPE == "mariadb":
    import json
    from lib_mdb_handler import db_handler, db_error
    with open(".login-info.txt") as login_info_file:  # Grab login data
        db_connection_parameters = json.load(login_info_file)

elif DB_TYPE == "sqlite3":
    from lib_sql_handler import db_handler, db_error
    db_connection_parameters = SQLITE3_LOCATION


# Because being lazy writes good code
class db_hlapi:

    def __init__(self, guild_id):
        self.database = db_handler(db_connection_parameters)
        self.guild = guild_id

    def __enter__(self):
        return self

    def grab_config(self, config):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_config", ["property",config])
        except db_error.OperationalError:
            self.create_guild_db()
            data = self.database.fetch_rows_from_table(f"{self.guild}_config", ["property",config])

        if data:
            return data[0][1]
        else:
            return []

    def add_config(self, config, value):

        try:
            data = self.database.add_to_table(f"{self.guild}_config", [["property",config],["value",value]])
        except db_error.OperationalError:
            self.create_guild_db()
            data = self.database.add_to_table(f"{self.guild}_config", [["property",config],["value",value]])

    def grab_user_infractions(self, userid):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["userID",userid])
        except db_error.OperationalError:
            self.create_guild_db()
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["userID",userid])

        return data

    # Check if a message is on the starboard already
    def in_starboard(self, message_id):
        
        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_starboard", ["messageID", message_id])
        except db_error.OperationalError:
            self.create_guild_db()
            data = self.database.fetch_rows_from_table(f"{self.guild}_starboard", ["messageID", message_id])
        
        if data:
            return True
        else:
            return False
        
    def add_to_starboard(self, message_id):

        try:
            self.database.add_to_table(f"{self.guild}_starboard", [["messageID", message_id]])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_starboard", [["messageID", message_id]])

        return True

    def grab_infraction(self, infractionID):

        try:
            infraction = self.database.fetch_rows_from_table(f"{self.guild}_infractions",["infractionID",infractionID])
        except db_error.OperationalError:
            self.create_guild_db()
            infraction = self.database.fetch_rows_from_table(f"{self.guild}_infractions",["infractionID",infractionID])

        if infraction:
            return infraction[0]
        else:
            return False

    def delete_infraction(self, infraction_id):

        try:
            self.database.delete_rows_from_table(f"{self.guild}_infractions",["infractionID",infraction_id])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.delete_rows_from_table(f"{self.guild}_infractions",["infractionID",infraction_id])

    def mute_user(self, user, endtime, infractionID):
        
        try:
            self.database.add_to_table(f"{self.guild}_mutes",[["infractionID", infractionID],["userID", user],["endMute",endtime]])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_mutes",[["infractionID", infractionID],["userID", user],["endMute",endtime]])

    def unmute_user(self, infractionID):
        
        try:
            self.database.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionID])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionID])

    def create_guild_db(self):
        
        self.database.make_new_table(f"{self.guild}_config",[["property", tuple, 1], ["value", str]])
        self.database.make_new_table(f"{self.guild}_infractions", [
        ["infractionID", tuple, 1],
        ["userID", str],
        ["moderatorID", str],
        ["type", str],
        ["reason", str],
        ["timestamp", int(64)]
        ])
        self.database.make_new_table(f"{self.guild}_starboard", [["messageID", tuple, 1]])
        self.database.make_new_table(f"{self.guild}_mutes", [["infractionID", tuple, 1],["userID", str],["endMute",int(64)]])

    def download_guild_db(self):

        dbdict = {
            "config":[["property","value"]],
            "infractions":[["infractionID","userID","moderatorID","type","reason","timestamp"]],
            "mutes":[["infractionID","userID","endMute"]],
            "starboard":[["messageID"]]
            }

        for i in ["config","infractions","starboard","mutes"]:
            try:
                dbdict[i].extend(self.database.fetch_table(f"{self.guild}_{i}"))
            except db_error.OperationalError:
                pass

        return dbdict

    def delete_guild_db(self):

        for i in ["config","infractions","starboard","mutes"]:
            try:
                self.database.delete_table(f"{self.guild}_{i}")
            except db_error.OperationalError:
                pass

    def add_infraction(self, infractionid, userid, moderatorid, infractiontype, reason, timestamp):

            try:
                self.database.add_to_table(f"{message.guild.id}_infractions", [
                ["infractionID", infractionid],
                ["userID", userid],
                ["moderatorID", moderatorid],
                ["type", infractiontype],
                ["reason", reason],
                ["timestamp", timestamp]
                ])
            except db_error.OperationalError:
                self.create_guild_db()
                self.database.add_to_table(f"{message.guild.id}_infractions", [
                ["infractionID", infractionid],
                ["userID", userid],
                ["moderatorID", moderatorid],
                ["type", infractiontype],
                ["reason", reason],
                ["timestamp", timestamp]
                ])

    def close(self):
        self.database.close()

    def __exit__(self, err_type, err_value, err_traceback):
        self.database.close()
        if err_type:
            raise err_type(err_value)
