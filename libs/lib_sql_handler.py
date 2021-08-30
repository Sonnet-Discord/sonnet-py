# SSQLH, simple sqlite3 handler
# Ultrabear 2020

import sqlite3
import io
from typing import List, Tuple, Any, Union


class db_error:  # DB error codes
    OperationalError = sqlite3.OperationalError
    InterfaceError = sqlite3.InterfaceError
    Error = sqlite3.Error


class db_handler:

    TEXT_KEY = True

    def __init__(self, db_location: str) -> None:
        self.con = sqlite3.connect(db_location)
        self.cur = self.con.cursor()
        self.closed: bool = False

    def __enter__(self) -> "db_handler":
        return self

    def make_new_index(self, tablename: str, indexname: str, columns: List[str]) -> None:

        # Test for attack
        if "\\" in tablename or "'" in tablename:
            raise db_error.OperationalError("Detected SQL injection attack")

        if "\\" in indexname or "'" in indexname:
            raise db_error.OperationalError("Detected SQL injection attack")

        cols = "', '".join(columns)
        db_inputStr = f"CREATE INDEX IF NOT EXISTS '{indexname}' ON '{tablename}' ('{cols}')"

        self.cur.execute(db_inputStr)

    def make_new_table(self, tablename: str, data: Union[List[Any], Tuple[Any, ...]]) -> None:

        # Load hashmap of python datatypes to SQLite3 datatypes
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

        # Test for attack
        if "\\" in tablename or "'" in tablename:
            raise db_error.OperationalError("Detected SQL injection attack")

        # Add table addition
        db_inputBuilder = io.StringIO()
        db_inputBuilder.write(f"CREATE TABLE IF NOT EXISTS '{tablename}' (")

        # Parse through table items, item with 3 entries is primary key
        inlist = []
        for i in data:
            if len(i) >= 3 and i[2] == 1:
                inlist.append(f"{i[0]} {datamap[i[1]]} PRIMARY KEY")
            else:
                inlist.append(f"{i[0]} {datamap[i[1]]}")

        # Add parsed inputs to inputStr
        db_inputBuilder.write(", ".join(inlist))
        db_inputBuilder.write(")")

        # Execute table generation
        self.cur.execute(db_inputBuilder.getvalue())

    def add_to_table(self, table: str, data: Union[List[Any], Tuple[Any, ...]]) -> None:

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        db_inputBuilder = io.StringIO()

        # Add insert data and generate base tables
        db_inputBuilder.write(f"REPLACE INTO '{table}' (")
        db_inputList = []

        db_inputBuilder.write(", ".join([i[0] for i in data]))
        db_inputBuilder.write(")\n")

        # Insert values data
        db_inputBuilder.write("VALUES (")
        db_inputBuilder.write(", ".join(["?" for i in range(len(data))]))
        db_inputBuilder.write(")\n")

        db_inputList.extend([i[1] for i in data])

        self.cur.execute(db_inputBuilder.getvalue(), tuple(db_inputList))

    def multicount_rows_from_table(self, table: str, searchparms: List[List[Any]]) -> int:

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        db_inputBuilder = io.StringIO()

        # Add SELECT data
        db_inputBuilder.write(f"SELECT COUNT(*) FROM '{table}' WHERE ")

        db_inputBuilder.write(" AND ".join([f"({i[0]} {i[2] if len(i) > 2 else '='} ?)" for i in searchparms]))
        db_inputList = [i[1] for i in searchparms]

        # Execute
        self.cur.execute(db_inputBuilder.getvalue(), tuple(db_inputList))

        retval: int = tuple(self.cur.fetchall())[0][0]
        return retval

    def fetch_rows_from_table(self, table: str, search: List[Any]) -> Tuple[Any, ...]:

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        # Add SELECT data
        db_inputStr = f"SELECT * FROM '{table}' WHERE {search[0]} {search[2] if len(search) > 2 else '='} ?"
        db_inputList = [search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

        return tuple(self.cur.fetchall())

    def multifetch_rows_from_table(self, table: str, searchparms: List[List[Any]]) -> Tuple[Any, ...]:

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        db_inputBuilder = io.StringIO()

        # Add SELECT data
        db_inputBuilder.write(f"SELECT * FROM '{table}' WHERE ")

        db_inputBuilder.write(" AND ".join([f"({i[0]} {i[2] if len(i) > 2 else '='} ?)" for i in searchparms]))
        db_inputList = [i[1] for i in searchparms]

        # Execute
        self.cur.execute(db_inputBuilder.getvalue(), tuple(db_inputList))

        return tuple(self.cur.fetchall())

    # deletes rows from table where column i[0] has value i[1]
    def delete_rows_from_table(self, table: str, column_search: List[Any]) -> None:

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        # Do deletion setup
        db_inputStr = f"DELETE FROM '{table}' WHERE {column_search[0]}=?"
        db_inputList = [column_search[1]]

        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))

    def delete_table(self, table: str) -> None:  # drops the table specified

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        self.cur.execute(f"DROP TABLE IF EXISTS '{table}';")

    def fetch_table(self, table: str) -> Tuple[Any, ...]:  # Fetches a full table

        # Test for attack
        if "\\" in table or "'" in table:
            raise db_error.OperationalError("Detected SQL injection attack")

        self.cur.execute(f"SELECT * FROM '{table}';")

        # Send data
        return tuple(self.cur.fetchall())

    def list_tables(self, searchterm: str) -> Tuple[str, ...]:

        self.cur.execute("SELECT name FROM sqlite_master WHERE name LIKE ?;", (searchterm, ))

        # Send data
        return tuple(self.cur.fetchall())

    def ping(self) -> None:
        self.con.commit()

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
