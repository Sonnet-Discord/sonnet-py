# Simple MariaDB handler
# Ultrabear 2020

import mariadb
from typing import List, Dict


class db_error:  # DB error codes
    OperationalError = mariadb.Error
    InterfaceError = mariadb.InterfaceError
    Error = mariadb.OperationalError


class db_handler:  # Im sorry I OOP'd it :c -ultrabear
    def __init__(self, login_info: Dict):
        # Connect to database with login info
        self.con = mariadb.connect(user=login_info["login"], password=login_info["password"], host=login_info["server"], database=login_info["db_name"], port=int(login_info["port"]))

        # Generate Cursor
        self.cur = self.con.cursor()

        # Save database name
        self.db_name = login_info["db_name"]

        self.closed = False

    def __enter__(self):
        return self

    def make_new_table(self, tablename: str, data: List[List]):

        # Load hashmap of python datatypes to MariaDB datatypes
        datamap = {
            int: "INT",
            str: "TEXT",
            bytes: "BLOB",
            tuple: "VARCHAR(255)",
            None: "NULL",
            float: "FLOAT",
            int(8): "TINYINT",
            int(16): "SMALLINT",
            int(24): "MEDIUMINT",
            int(32): "INT",
            int(64): "BIGINT",
            str(8): "TINYTEXT",
            str(16): "TEXT",
            str(24): "MEDIUMTEXT",
            str(32): "LONGTEXT",
            bytes(8): "TINYBLOB",
            bytes(16): "BLOB",
            bytes(24): "MEDIUMBLOB",
            bytes(32): "LONGBLOB"
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
        db_inputStr += ", ".join(inlist) + ")"

        # Exectute table generation
        self.cur.execute(db_inputStr)

    def add_to_table(self, table: str, data: List[List]):

        # Add insert data and generate base tables
        db_inputStr = f"REPLACE INTO {table} ("
        db_inputList = []
        db_inputStr += ", ".join([i[0] for i in data]) + ")\n"

        # Insert values data
        db_inputStr += "VALUES ("
        db_inputList.extend([i[1] for i in data])
        db_inputStr += ", ".join(["?" for i in data]) + ")\n"

        self.cur.execute(db_inputStr, tuple(db_inputList))

    def fetch_rows_from_table(self, table: str, collumn_search: List):

        # Add SELECT data
        db_inputStr = f"SELECT * FROM {table} WHERE {collumn_search[0]}=?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def delete_rows_from_table(self, table: str, collumn_search: List):

        # Do deletion setup
        db_inputStr = f"DELETE FROM {table} WHERE {collumn_search[0]}=?"
        db_inputList = [collumn_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

    def delete_table(self, table: str):

        self.cur.execute(f"DROP TABLE IF EXISTS {table};")

    def fetch_table(self, table: str):

        self.cur.execute(f"SELECT * FROM {table};")

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def list_tables(self, searchterm: str):

        self.cur.execute(f"SHOW TABLES WHERE Tables_in_{self.db_name} LIKE ?", (searchterm, ))

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def commit(self):  # Commits data to db
        self.con.commit()

    def close(self):
        self.con.commit()
        self.con.close()
        self.closed = True

    def __del__(self):
        if not self.closed:
            self.close()

    def __exit__(self, err_type, err_value, err_traceback):
        self.con.commit()
        self.con.close()
        self.closed = True
        if err_type:
            raise err_type(err_value)
