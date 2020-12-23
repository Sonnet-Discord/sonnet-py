# Simple MariaDB handler
# Ultrabear 2020

import mariadb, json

class db_error: # DB error codes
    OperationalError = mariadb.Error


class db_handler:  # Im sorry I OOP'd it :c -ultrabear
    def __init__(self):
        with open(".login-info.txt") as login_info_file:  # Grab login data
            login_info = json.load(login_info_file)

        # Connect to database with login info
        self.con = mariadb.connect(
            user = login_info["login"],
            password = login_info["password"],
            host = login_info["server"],
            database = login_info["db_name"],
            port = int(login_info["port"]) )

        # Generate Cursor
        self.cur = self.con.cursor()

    def __enter__(self):
        return self

    def make_new_table(self, tablename, data):

        # Load hashmap of python datatypes to MariaDB datatypes
        datamap = {
            int:"INT", str:"TEXT", bytes:"BLOB", tuple:"VARCHAR(255)", None:"NULL", float:"FLOAT",
            int(8):"TINYINT", int(16):"SMALLINT", int(24):"MEDIUMINT", int(32):"INT", int(64):"BIGINT",
            str(8):"TINYTEXT", str(16):"TEXT", str(24):"MEDIUMTEXT", str(32):"LONGTEXT",
            bytes(8):"TINYBLOB", bytes(16):"BLOB", bytes(24):"MEDIUMBLOB", bytes(32):"LONGBLOB"
        }

        # Add table addition
        db_inputStr = f'CREATE TABLE IF NOT EXISTS {tablename} ('

        # Parse through table items, item with 3 entries is primary key
        inlist = []
        for i in data:
            if len(i) >= 3 and i[2] == 1:
                inlist.append(f"{i[0]} {datamap[i[1]]} PRIMARY KEY")
            else:
                inlist.append(f"{i[0]} {datamap[i[1]]}")

        # Add parsed inputs to inputStr
        db_inputStr += ", ". join(inlist) + ")"

        # Exectute table generation
        self.cur.execute(db_inputStr)

    def add_to_table(self, table, data):

        # Add insert data and generate base tables
        db_inputStr = f"REPLACE INTO {table} ("
        db_inputList = []
        db_inputStr += ", ".join([i[0] for i in data])+ ")\n"

        # Insert values data
        db_inputStr += "VALUES ("
        db_inputList.extend([i[1] for i in data])
        db_inputStr += ", ".join(["?" for i in data])+ ")\n"

        self.cur.execute(db_inputStr, tuple(db_inputList))

    def fetch_rows_from_table(self, table, collumn_search):

        # Add SELECT data
        db_inputStr = f"SELECT * FROM {table} WHERE {collumn_search[0]}=?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        # Send data
        returndata = list(self.cur)
        return returndata

    def delete_rows_from_table(self, table, collumn_search):

        # Do deletion setup
        db_inputStr = f"DELETE FROM {table} WHERE {collumn_search[0]}=?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

    def delete_table(self, table):

        self.cur.execute(f"DROP TABLE IF EXISTS {table};")

    def fetch_table(self, table):

        self.cur.execute(f"SELECT * FROM {table};")

        # Send data
        returndata = list(self.cur)
        return returndata

    def commit(self):  # Commits data to db
        self.con.commit()

    def close(self):
        self.con.commit()
        self.con.close()

    def __exit__(self, err_type, err_value, err_traceback):
        self.con.commit()
        self.con.close()
        if err_type:
            raise err_type(err_value)


# Because being lazy writes good code
class db_hlapi:

    def __init__(self, guild_id):
        self.database = db_handler()
        self.guild = guild_id

    def __enter__(self):
        return self

    def grab_config(self, config):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_config", ["property",config])
        except db_error.OperationalError:
            data = []

        if data:
            return data[0][1]
        else:
            return []

    def grab_user_infractions(self, userid):

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["userID",userid])
        except db_error.OperationalError:
            data = []

        return data

    # Check if a message is on the starboard already
    def in_starboard(self, message_id):
        
        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_starboard", ["messageID", message_id])
        except db_error.OperationalError:
            data = True
        
        if data:
            return True
        else:
            return False
        
    def add_to_starboard(self, message_id):

        try:
            self.database.add_to_table(f"{self.guild}_starboard", [["messageID", message_id]])
        except db_error.OperationalError:
            return False

        return True

    def grab_infraction(self, infractionID):

        try:
            infraction = self.database.fetch_rows_from_table(f"{self.guild}_infractions",["infractionID",infractionID])
        except db_error.OperationalError:
            infraction = None

        if infraction:
            return infraction[0]
        else:
            return False

    def delete_infraction(self, infraction_id):

        try:
            self.database.delete_rows_from_table(f"{self.guild}_infractions",["infractionID",infraction_id])
        except db_error.OperationalError:
            pass

    def mute_user(self, user, endtime, infractionID):
        
        self.database.add_to_table(f"{self.guild}_mutes",[["infractionID", infractionID],["userID", user],["endMute",endtime]])

    def unmute_user(self, infractionID):
        
        self.database.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionID])


    def close(self):
        self.database.close()

    def __exit__(self, err_type, err_value, err_traceback):
        self.database.close()
        if err_type:
            raise err_type(err_value)
