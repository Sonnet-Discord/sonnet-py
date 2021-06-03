# Simple MariaDB handler
# Ultrabear 2020

import mariadb
from typing import List, Dict, Any, Tuple, Union

mdb_version = tuple([int(i) for i in mariadb.mariadbapi_version.split(".")])


class db_error:  # DB error codes
    OperationalError = mariadb.Error
    InterfaceError = mariadb.InterfaceError
    Error = mariadb.OperationalError


class db_handler:  # Im sorry I OOP'd it :c -ultrabear
    @property
    def TEXT_KEY(self) -> bool:
        return self.con.get_server_version() >= (10, 4)

    def __init__(self, login_info: Dict[str, Any]) -> None:
        # Connect to database with login info
        self.con = mariadb.connect(user=login_info["login"], password=login_info["password"], host=login_info["server"], database=login_info["db_name"], port=int(login_info["port"]))

        # Generate Cursor
        self.cur = self.con.cursor()

        # Save database name
        self.db_name = login_info["db_name"]

        self.closed = False

    def __enter__(self):
        return self

    def make_new_index(self, tablename: str, indexname: str, columns: List[str]) -> None:

        db_inputStr = f"CREATE INDEX IF NOT EXISTS {indexname} ON {tablename} ({', '.join(columns)})"

        self.cur.execute(db_inputStr)

    def make_new_table(self, tablename: str, data: Union[List[Any], Tuple[Any, ...]]) -> None:

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

        # Execute table generation
        self.cur.execute(db_inputStr)

    def add_to_table(self, table: str, data: Union[List[Any], Tuple[Any, ...]]) -> None:

        # Add insert data and generate base tables
        db_inputStr = f"REPLACE INTO {table} ("
        db_inputList = []
        db_inputStr += ", ".join([i[0] for i in data]) + ")\n"

        # Insert values data
        db_inputStr += "VALUES ("
        db_inputList.extend([i[1] for i in data])
        db_inputStr += ", ".join(["?" for i in data]) + ")\n"

        self.cur.execute(db_inputStr, tuple(db_inputList))

    def multicount_rows_from_table(self, table: str, searchparms: List[List[Any]]) -> int:

        # Add SELECT data
        db_inputStr = f"SELECT COUNT(*) FROM {table} WHERE "

        db_inputStr += " AND ".join([f"({i[0]} {i[2] if len(i) > 2 else '='} ?)" for i in searchparms])
        db_inputList = [i[1] for i in searchparms]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        retval: int = tuple(self.cur)[0][0]
        return retval

    def fetch_rows_from_table(self, table: str, search: List[Any]) -> Tuple[Any, ...]:

        # Add SELECT data
        db_inputStr = f"SELECT * FROM {table} WHERE {search[0]} {search[2] if len(search) > 2 else '='} ?"
        db_inputList = [search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def multifetch_rows_from_table(self, table: str, searchparms: List[List[Any]]) -> Tuple[Any, ...]:

        # Add SELECT data
        db_inputStr = f"SELECT * FROM {table} WHERE "

        db_inputStr += " AND ".join([f"({i[0]} {i[2] if len(i) > 2 else '='} ?)" for i in searchparms])
        db_inputList = [i[1] for i in searchparms]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        return tuple(self.cur)

    def delete_rows_from_table(self, table: str, column_search: List[Any]) -> None:

        # Do deletion setup
        db_inputStr = f"DELETE FROM {table} WHERE {column_search[0]}=?"
        db_inputList = [column_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

    def delete_table(self, table: str) -> None:

        self.cur.execute(f"DROP TABLE IF EXISTS {table};")

    def fetch_table(self, table: str) -> Tuple[Any, ...]:

        self.cur.execute(f"SELECT * FROM {table};")

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def list_tables(self, searchterm: str) -> Tuple[Any, ...]:

        self.cur.execute(f"SHOW TABLES WHERE Tables_in_{self.db_name} LIKE ?", (searchterm, ))

        # Send data
        returndata = tuple(self.cur)
        return returndata

    def ping(self) -> None:
        self.con.ping()

    def commit(self) -> None:  # Commits data to db
        self.con.commit()

    def close(self) -> None:
        self.con.commit()
        self.con.close()
        self.closed = True

    def __del__(self) -> None:
        if not self.closed:
            self.close()

    def __exit__(self, err_type: Any, err_value: Any, err_traceback: Any) -> None:
        self.con.commit()
        self.con.close()
        self.closed = True
        if err_type:
            raise err_type(err_value)
