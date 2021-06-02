# High Level API calls for sonnet style databases
# Ultrabear 2020

import importlib

import threading

from sonnet_cfg import DB_TYPE, SQLITE3_LOCATION

from typing import Union, Dict, List, Tuple, Optional, Any, Type, cast

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
    from lib_sql_handler import db_handler, db_error  # type: ignore[misc]
    db_connection_parameters = SQLITE3_LOCATION


class DATABASE_FATAL_CONNECTION_LOSS(Exception):
    pass


try:
    db_connection = db_handler(db_connection_parameters)
except db_error.Error:
    print("FATAL: DATABASE CONNECTION ERROR")
    raise DATABASE_FATAL_CONNECTION_LOSS("Database failure")


def db_grab_connection() -> db_handler:
    global db_connection
    try:
        db_connection.ping()
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
    def __init__(self, guild_id: Optional[int], lock: Optional[threading.Lock] = None) -> None:
        self.database = db_grab_connection()
        self.guild: Optional[int] = guild_id
        self._lock: Optional[threading.Lock] = lock

        self.__enum_input: Dict[str, List[Tuple[str, type]]] = {}
        self.__enum_pool: Dict[str, List[Tuple[Any, ...]]] = {}

        self.inject_enum("config", [("property", str), ("value", str)])
        self.inject_enum("infractions", [("infractionID", str), ("userID", str), ("moderatorID", str), ("type", str), ("reason", str), ("timestamp", int)])
        self.inject_enum("mutes", [("infractionID", str), ("userID", str), ("endMute", int)])

    def __enter__(self) -> "db_hlapi":
        if self._lock:
            self._lock.acquire()
        return self

    def _validate_enum(self, schema: List[Tuple[str, type]]) -> bool:
        for i in schema:
            if type(i[0]) != str or i[1] not in [str, int]:
                return False
        return True

    def inject_enum(self, enumname: str, schema: List[Tuple[str, type]]) -> None:
        if not self._validate_enum(schema):
            raise TypeError("Invalid schema passed")

        # Inject Primary key
        PK, T = schema[0]
        if T == str:
            pks: Any = (PK, tuple, 1)
        elif T == int:
            pks = (PK, int(64), 1)

        cols: List[Any] = [pks]
        # Inject rest of table
        for col in schema[1:]:
            if col[1] == str:
                cols.append(col)
            elif col[1] == int:
                cols.append((
                    col[0],
                    int(64),
                    ))

        self.__enum_input[enumname] = schema
        self.__enum_pool[enumname] = cols

    def grab_enum(self, name: str, cname: Union[str, int]) -> Optional[List[Union[str, int]]]:
        if name not in self.__enum_pool:
            raise TypeError(f"Trying to grab from table that is not registered ({name} not registered)")

        if type(cname) != self.__enum_input[name][0][1]:
            raise TypeError("grab type does not match enum PK signature")

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_{name}", [self.__enum_input[name][0][0], cname])
        except db_error.OperationalError:
            return None

        return data[0] if data else None

    def set_enum(self, name: str, cpush: List[Union[str, int]]) -> None:
        if name not in self.__enum_pool:
            raise TypeError(f"Trying to set to table that is not registered ({name})")

        if len(cpush) != len(self.__enum_input[name]):
            raise TypeError(f"Length of table does not match length of input ({len(cpush)} != {len(self.__enum_input[name])})")

        for index, i in enumerate(cpush):
            if type(i) != self.__enum_input[name][index][1]:
                raise TypeError(f"Improper type passed based on enum registry (type '{type(i).__name__}' is not type '{self.__enum_input[name][index][1].__name__}')")

        push = tuple(zip(map(lambda i: i[0], self.__enum_input[name]), cpush))

        try:
            self.database.add_to_table(f"{self.guild}_{name}", push)
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_{name}", push)

    def create_guild_db(self) -> None:
        for i in self.__enum_pool:
            self.database.make_new_table(f"{self.guild}_{i}", self.__enum_pool[i])

    def grab_config(self, config: str) -> Optional[str]:

        try:
            data: Optional[Tuple[List[Any], ...]] = self.database.fetch_rows_from_table(f"{self.guild}_config", ["property", config])
        except db_error.OperationalError:
            data = None

        return data[0][1] if data else None

    def add_config(self, config: str, value: str) -> None:

        try:
            self.database.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])

    def delete_config(self, config: str) -> None:

        try:
            self.database.delete_rows_from_table(f"{self.guild}_config", ["property", config])
        except db_error.OperationalError:
            pass

    # Grab infractions of a user
    def grab_user_infractions(self, userid: Union[int, str]) -> Tuple[List[Union[str, int]], ...]:
        """
        Deprecated, replaced by grab_filter_infractions
        """

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["userID", userid])
        except db_error.OperationalError:
            data = tuple()

        return data

    # grab infractions dealt by a mod
    def grab_moderator_infractions(self, moderatorid: Union[int, str]) -> Tuple[Any, ...]:
        """
        Deprecated, replaced by grab_filter_infractions
        """

        try:
            data = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["moderatorID", moderatorid])
        except db_error.OperationalError:
            data = tuple()

        return data

    def grab_filter_infractions(self,
                                user: Optional[int] = None,
                                moderator: Optional[int] = None,
                                itype: Optional[str] = None,
                                automod: bool = True,
                                count: bool = False) -> Union[Tuple[str, str, str, str, str, int], int]:

        schm: List[List[str]] = []
        if user:
            schm.append(["userID", str(user)])
        if moderator:
            schm.append(["moderatorID", str(moderator)])
        if itype:
            schm.append(["type", itype])
        if not automod:
            schm.append(["reason", "[AUTOMOD]%", "NOT LIKE"])

        db_type = Union[Tuple[str, str, str, str, str, int], int]

        try:
            if self.database.TEXT_KEY:
                self.database.make_new_index(f"{self.guild}_infractions", f"{self.guild}_infractions_users", ["userID"])
                self.database.make_new_index(f"{self.guild}_infractions", f"{self.guild}_infractions_moderators", ["moderatorID"])
            if count:
                data = cast(db_type, self.database.multicount_rows_from_table(f"{self.guild}_infractions", schm))
            else:
                data = cast(db_type, self.database.multifetch_rows_from_table(f"{self.guild}_infractions", schm))
        except db_error.OperationalError:
            data = cast(db_type, tuple()) if not count else 0

        return data

    # Check if a message is on the starboard already
    def in_starboard(self, message_id: int) -> bool:
        """
        Deprecated as starboard is now expected to use enums directly
        """

        self.inject_enum("starboard", [
            ("messageID", str),
            ])
        return bool(self.grab_enum("starboard", str(message_id)))

    def add_to_starboard(self, message_id: int) -> bool:
        """
        Deprecated as starboard is now expected to use enums directly
        """

        self.inject_enum("starboard", [
            ("messageID", str),
            ])
        self.set_enum("starboard", [str(message_id)])
        return True

    def grab_infraction(self, infractionID: str) -> Optional[Tuple[str, str, str, str, str, int]]:

        try:
            infraction: Any = self.database.fetch_rows_from_table(f"{self.guild}_infractions", ["infractionID", infractionID])
        except db_error.OperationalError:
            infraction = None

        return infraction[0] if infraction else None

    def delete_infraction(self, infraction_id: str) -> None:

        try:
            self.database.delete_rows_from_table(f"{self.guild}_infractions", ["infractionID", infraction_id])
        except db_error.OperationalError:
            pass

    def mute_user(self, user: int, endtime: int, infractionID: str) -> None:

        try:
            self.database.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])

    def unmute_user(self, infractionid: Optional[str] = None, userid: Optional[int] = None) -> None:

        try:
            if infractionid:
                self.database.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionid])
            if userid:
                self.database.delete_rows_from_table(f"{self.guild}_mutes", ["userid", userid])
        except db_error.OperationalError:
            pass

    def download_guild_db(self) -> Dict[str, List[List[str]]]:

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

    def upload_guild_db(self, dbdict: Dict[str, List[List[Any]]]) -> bool:

        reimport = {
            "config": [["property", "value"]],
            "infractions": [["infractionID", "userID", "moderatorID", "type", "reason", "timestamp"]],
            "mutes": [["infractionID", "userID", "endMute"]],
            "starboard": [["messageID"]]
            }

        for i in reimport.keys():
            if i in dbdict:
                reimport[i].extend(dbdict[i][1:])

        self.create_guild_db()

        for i in reimport.keys():
            for row in reimport[i][1:]:
                try:
                    self.database.add_to_table(f"{self.guild}_{i}", tuple(zip(reimport[i][0], row)))
                except db_error.OperationalError:
                    return False

        return True

    def delete_guild_db(self) -> None:

        for i in ["config", "infractions", "starboard", "mutes"]:
            try:
                self.database.delete_table(f"{self.guild}_{i}")
            except db_error.OperationalError:
                pass

    def add_infraction(self, *din: Union[int, str]) -> None:

        quer = tuple(zip(("infractionID", "userID", "moderatorID", "type", "reason", "timestamp"), din))

        try:
            self.database.add_to_table(f"{self.guild}_infractions", quer)
        except db_error.OperationalError:
            self.create_guild_db()
            self.database.add_to_table(f"{self.guild}_infractions", quer)

    def fetch_all_mutes(self) -> List[Tuple[str, str, str, int]]:

        # Grab list of tables
        tablelist = self.database.list_tables("%_mutes")

        mutetable: List[Tuple[str, str, str, int]] = []
        for i in tablelist:
            mutetable.extend([(i[0][:-6], ) + tuple(a) for a in self.database.fetch_table(i[0])])  # type: ignore[misc]

        return mutetable

    def is_muted(self, userid: Optional[int] = None, infractionid: Optional[str] = None) -> bool:

        try:
            if userid:
                muted = bool(self.database.fetch_rows_from_table(f"{self.guild}_mutes", ["userID", userid]))
            elif infractionid:
                muted = bool(self.database.fetch_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionid]))
        except db_error.OperationalError:
            muted = False

        return muted

    def close(self) -> None:
        self.database.commit()

    def __exit__(self, err_type: Optional[Type[Exception]], err_value: Optional[str], err_traceback: Any) -> None:
        if self._lock:
            self._lock.release()
        self.database.commit()
        if err_type:
            raise err_type(err_value)
