# SSQLH, simple sqlite3 handler
# Ultrabear 2020

import sqlite3

class db_error: # DB error codes
    OperationalError = sqlite3.OperationalError

class db_handler:  # Im sorry I OOP'd it :c -ultrabear
    def __init__(self, dbloc):
        self.con = sqlite3.connect(dbloc)
        self.cur = self.con.cursor()
        
    def __enter__(self):
        return self
    
    def make_new_table(self, tablename, data):
        
        # Load hashmap of python datatypes to SQLite3 datatypes
        datamap = {int:"INTEGER", None:"NULL", float:"REAL", str:"TEXT", bytes:"TEXT"}
        
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
    
    def add_to_table(self, table, data):
        
        # Add insert data and generate base tables
        db_inputStr = f"INSERT INTO {table} ("
        db_inputList = []
        db_inputStr += ", ".join([i[0] for i in data])+ ")\n"
        
        # Insert values data
        db_inputStr += "VALUES ("
        db_inputList.extend([i[1] for i in data])
        db_inputStr += ", ".join(["?" for i in range(len(data))])+ ")\n"
        
        # Insert on conflict data
        db_inputStr += f"ON CONFLICT ({data[0][0]}) DO UPDATE SET\n    VALUE = excluded.value\n"
        
        # Insert WHERE data
        db_inputStr += f"WHERE {data[0][0]} = ?"
        db_inputList.append(data[0][1])

        self.cur.execute(db_inputStr, tuple(db_inputList))
    
    def fetch_rows_from_table(self, table, collum_search):
        
        # Add SELECT data
        db_inputStr = f"SELECT * FROM {table} WHERE {collum_search[0]} = ?"
        db_inputList = [collum_search[1]]
        
        # Execute
        self.cur.execute(db_inputStr, tuple(db_inputList))
        return self.cur.fetchall()
    
    def close(self):
        self.con.commit()
        self.con.close()
    
    def __exit__(self, err_type, err_value, err_traceback):
        if err_type:
            raise err_type(err_value)
        self.con.commit()
        self.con.close()
