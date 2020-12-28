# SSQLH, simple sqlite3 handler
# Ultrabear 2020

import sqlite3

class db_error: # DB error codes
    OperationalError = sqlite3.OperationalError

class db_handler:
    def __init__(self, db_location):
        self.con = sqlite3.connect(db_location)
        self.cur = self.con.cursor()

    def __enter__(self):
        return self

    def make_new_table(self, tablename, data):

        # Load hashmap of python datatypes to SQLite3 datatypes
        datamap = {
            int:"INT", str:"TEXT", bytes:"BLOB", tuple:"VARCHAR(255)", None:"NULL", float:"FLOAT",
            int(8):"TINYINT", int(16):"SMALLINT", int(24):"MEDIUMINT", int(32):"INT", int(64):"BIGINT",
            str(8):"TINYTEXT", str(16):"TEXT", str(24):"MEDIUMTEXT", str(32):"LONGTEXT",
            bytes(8):"TINYBLOB", bytes(16):"BLOB", bytes(24):"MEDIUMBLOB", bytes(32):"LONGBLOB"
        }

        # Test for attack
        if tablename.count("\\") or tablename.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        # Add table addition
        db_inputStr = f"CREATE TABLE IF NOT EXISTS '{tablename}' ("

        # Parse through table items, item with 3 entries is primary key
        inlist = []
        for i in data:
            if len(i) >= 3 and i[2] == 1:
                inlist.append(f"{i[0]} {datamap[i[1]]} PRIMARY KEY")
            else:
                inlist.append(f"{i[0]} {datamap[i[1]]}")

        # Add parsed inputs to inputStr 
        db_inputStr += ", ".join(inlist) + ")"

        # Exectute table generation
        self.cur.execute(db_inputStr)

    def add_to_table(self, table, data):

        # Test for attack
        if table.count("\\") or table.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        # Add insert data and generate base tables
        db_inputStr = f"REPLACE INTO '{table}' ("
        db_inputList = []
        db_inputStr += ", ".join([i[0] for i in data])+ ")\n"

        # Insert values data
        db_inputStr += "VALUES ("
        db_inputList.extend([i[1] for i in data])
        db_inputStr += ", ".join(["?" for i in range(len(data))])+ ")\n"

        self.cur.execute(db_inputStr, tuple(db_inputList))

    def fetch_rows_from_table(self, table, collumn_search):

        # Test for attack
        if table.count("\\") or table.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        # Add SELECT data
        db_inputStr = f"SELECT * FROM '{table}' WHERE {collumn_search[0]} = ?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))
        return self.cur.fetchall()

    # deletes rows from table where collumn i[0] has value i[1]
    def delete_rows_from_table(self, table, collumn_search): 

        # Test for attack
        if table.count("\\") or table.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        # Do deletion setup
        db_inputStr = f"DELETE FROM '{table}' WHERE {collumn_search[0]}=?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

    def delete_table(self, table): # drops the table specified

        # Test for attack
        if table.count("\\") or table.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        self.cur.execute(f"DROP TABLE IF EXISTS '{table}';")

    def fetch_table(self, table): # Fetches a full table

        # Test for attack
        if table.count("\\") or table.count("'"):
            raise db_error.OperationalError("Detected SQL injection attack")

        self.cur.execute(f"SELECT * FROM '{table}';")

        # Send data
        returndata = list(self.cur.fetchall())
        return returndata

    def list_tables(self, searchterm):

        self.cur.execute("SELECT name FROM sqlite_master WHERE name LIKE ?;", (searchterm,))

        # Send data
        returndata = list(self.cur.fetchall())
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
