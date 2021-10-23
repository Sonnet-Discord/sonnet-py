# High Level API calls for sonnet style databases
# Ultrabear 2020

import importlib

import threading, warnings, io

import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)

from lib_sonnetconfig import DB_TYPE, SQLITE3_LOCATION

from typing import Union, Dict, List, Tuple, Optional, Any, Type, cast

# Get db handling library
if DB_TYPE == "mariadb":
    import lib_mdb_handler
    importlib.reload(lib_mdb_handler)
    import json
    from lib_mdb_handler import db_handler, db_error
    with open(".login-info.txt", encoding="utf-8") as login_info_file:  # Grab login data
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


def db_grab_connection() -> db_handler:  # pytype: disable=invalid-annotation
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

    __slots__ = "_db", "database", "guild", "hlapi_version", "_sonnet_db_version", "__enum_input", "__enum_pool"

    def __init__(self, guild_id: Optional[int], lock: Optional[threading.Lock] = None) -> None:
        self._db = db_grab_connection()
        self.database = self._db  # Deprecated name
        self.guild: Optional[int] = guild_id

        self.hlapi_version = (1, 2, 9)
        self._sonnet_db_version = self._get_db_version()

        if lock:
            warnings.warn("db_hlapi(lock: threading.Lock) is deprecated", DeprecationWarning)

        self.__enum_input: Dict[str, List[Tuple[str, Type[Union[str, int]]]]] = {}
        self.__enum_pool: Dict[str, List[Tuple[Any, ...]]] = {}

        self.inject_enum("config", [("property", str), ("value", str)])
        self.inject_enum("infractions", [("infractionID", str), ("userID", str), ("moderatorID", str), ("type", str), ("reason", str), ("timestamp", int)])
        self.inject_enum("mutes", [("infractionID", str), ("userID", str), ("endMute", int)])

    def __enter__(self) -> "db_hlapi":
        return self

    def _get_db_version(self) -> Tuple[int, int, int]:
        try:
            d = self._db.fetch_rows_from_table("version_info", ["property", "db_version"])
            if d:
                ver = [int(i) for i in d[0][1].split(".")]
                return ver[0], ver[1], ver[2]  # mypy caused this
            else:
                self._db.add_to_table("version_info", [["property", "db_version"], ["value", "1.0.0"]])
                return (1, 0, 0)
        except db_error.OperationalError:
            self._db.make_new_table("version_info", [("property", tuple, 1), ("value", str)])
            self._db.add_to_table("version_info", [["property", "db_version"], ["value", "1.0.0"]])
            return (1, 0, 0)

    def _validate_enum(self, schema: List[Tuple[str, Type[Union[str, int]]]]) -> bool:
        for i in schema:
            if type(i[0]) != str or i[1] not in [str, int]:
                return False
        return True

    def inject_enum(self, enumname: str, schema: List[Tuple[str, Type[Union[str, int]]]]) -> None:
        """
        Add a custom table schema to the database

        :raises: TypeError - The schema passed is not valid
        """
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
        """
        Grab an item from the database table based on the first value

        This does not create a new enum, there are zero ways to modify an enum after it has been registered
        And an enum may only be registered through inject_enum

        :raises: TypeError - The table name is not registered or the requested key is not the correct type
        """
        if name not in self.__enum_pool:
            raise TypeError(f"Trying to grab from table that is not registered ({name} not registered)")

        if not isinstance(cname, self.__enum_input[name][0][1]):
            raise TypeError("grab type does not match enum PK signature")

        try:
            data = self._db.fetch_rows_from_table(f"{self.guild}_{name}", [self.__enum_input[name][0][0], cname])
        except db_error.OperationalError:
            return None

        return data[0] if data else None

    def set_enum(self, name: str, cpush: List[Union[str, int]]) -> None:
        """
        Set an item into the database table with a list of values

        This does not create a new enum, there are zero ways to modify an enum after it has been registered
        And an enum may only be registered through inject_enum

        :raises: TypeError - The table name is not registered or the types in the list do not match the table schema
        """
        if name not in self.__enum_pool:
            raise TypeError(f"Trying to set to table that is not registered ({name})")

        if len(cpush) != len(self.__enum_input[name]):
            raise TypeError(f"Length of table does not match length of input ({len(cpush)} != {len(self.__enum_input[name])})")

        for index, i in enumerate(cpush):
            if not isinstance(i, self.__enum_input[name][index][1]):
                errtuple = self.__enum_input[name][index]
                errbuilder = io.StringIO()
                errbuilder.write(f"Improper type passed based on enum registry, index: {index} name: {errtuple[0]}\n")
                errbuilder.write(f"(given type '{type(i).__name__}' is not type '{errtuple[1].__name__}')")
                raise TypeError(errbuilder.getvalue())

        push = tuple(zip(map(lambda i: i[0], self.__enum_input[name]), cpush))

        try:
            self._db.add_to_table(f"{self.guild}_{name}", push)
        except db_error.OperationalError:
            self.create_guild_db()
            self._db.add_to_table(f"{self.guild}_{name}", push)

    def delete_enum(self, enumname: str, key: str) -> None:
        """
        Deletes a row in an enums table based on primary key

        This does not create a new enum, there are zero ways to modify an enum after it has been registered
        And an enum may only be registered through inject_enum

        :raises: TypeError - The table name is not registered or the requested key is not the correct type
        """
        if enumname not in self.__enum_pool:
            raise TypeError(f"Trying to delete from table that is not registered ({enumname} not registered)")

        if not isinstance(key, self.__enum_input[enumname][0][1]):
            raise TypeError("delete type does not match enum PK signature")

        try:
            self._db.delete_rows_from_table(f"{self.guild}_{enumname}", [self.__enum_input[enumname][0][0], key])
        except db_error.OperationalError:
            pass

    def create_guild_db(self) -> None:
        """
        Create a guilds database
        This function is mainly for internal use as db calls will automatically create a db if it does not exist
        """
        for i in self.__enum_pool:
            self._db.make_new_table(f"{self.guild}_{i}", self.__enum_pool[i])

    def grab_config(self, config: str) -> Optional[str]:
        """
        Grabs a config from the guilds config table

        :returns: Optional[str] - The configuration value
        """

        try:
            data: Optional[Tuple[List[Any], ...]] = self._db.fetch_rows_from_table(f"{self.guild}_config", ["property", config])
        except db_error.OperationalError:
            data = None

        return data[0][1] if data else None

    def add_config(self, config: str, value: str) -> None:
        """
        Adds a config to the guilds config table
        """

        try:
            self._db.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])
        except db_error.OperationalError:
            self.create_guild_db()
            self._db.add_to_table(f"{self.guild}_config", [["property", config], ["value", value]])

    def delete_config(self, config: str) -> None:

        try:
            self._db.delete_rows_from_table(f"{self.guild}_config", ["property", config])
        except db_error.OperationalError:
            pass

    # Grab infractions of a user
    def grab_user_infractions(self, userid: Union[int, str]) -> Tuple[List[Union[str, int]], ...]:
        """
        Deprecated, replaced by grab_filter_infractions
        """
        warnings.warn("grab_user_infractions is Deprecated, use grab_filter_infractions instead", DeprecationWarning)

        try:
            data = self._db.fetch_rows_from_table(f"{self.guild}_infractions", ["userID", userid])
        except db_error.OperationalError:
            data = tuple()

        return data

    # grab infractions dealt by a mod
    def grab_moderator_infractions(self, moderatorid: Union[int, str]) -> Tuple[Any, ...]:
        """
        Deprecated, replaced by grab_filter_infractions
        """
        warnings.warn("grab_moderator_infractions is Deprecated, use grab_filter_infractions instead", DeprecationWarning)

        try:
            data = self._db.fetch_rows_from_table(f"{self.guild}_infractions", ["moderatorID", moderatorid])
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
        if user is not None:
            schm.append(["userID", str(user)])
        if moderator is not None:
            schm.append(["moderatorID", str(moderator)])
        if itype is not None:
            schm.append(["type", itype])
        if not automod:
            schm.append(["reason", "[AUTOMOD]%", "NOT LIKE"])

        db_type = Union[Tuple[str, str, str, str, str, int], int]

        try:
            if self._db.TEXT_KEY:
                self._db.make_new_index(f"{self.guild}_infractions", f"{self.guild}_infractions_users", ["userID"])
                self._db.make_new_index(f"{self.guild}_infractions", f"{self.guild}_infractions_moderators", ["moderatorID"])
            if count:
                data = cast(db_type, self._db.multicount_rows_from_table(f"{self.guild}_infractions", schm))
            else:
                data = cast(db_type, self._db.multifetch_rows_from_table(f"{self.guild}_infractions", schm))
        except db_error.OperationalError:
            data = cast(db_type, tuple()) if not count else 0

        return data

    # Check if a message is on the starboard already
    def in_starboard(self, message_id: int) -> bool:
        """
        Deprecated as starboard is now expected to use enums directly
        """
        warnings.warn("in_starboard is Deprecated, use db enums functions instead", DeprecationWarning)

        self.inject_enum("starboard", [
            ("messageID", str),
            ])
        return bool(self.grab_enum("starboard", str(message_id)))

    def add_to_starboard(self, message_id: int) -> bool:
        """
        Deprecated as starboard is now expected to use enums directly
        """
        warnings.warn("add_to_starboard is Deprecated, use db enums functions instead", DeprecationWarning)

        self.inject_enum("starboard", [
            ("messageID", str),
            ])
        self.set_enum("starboard", [str(message_id)])
        return True

    def grab_infraction(self, infractionID: str) -> Optional[Tuple[str, str, str, str, str, int]]:

        try:
            infraction: Any = self._db.fetch_rows_from_table(f"{self.guild}_infractions", ["infractionID", infractionID])
        except db_error.OperationalError:
            infraction = None

        return infraction[0] if infraction else None

    def delete_infraction(self, infraction_id: str) -> None:

        try:
            self._db.delete_rows_from_table(f"{self.guild}_infractions", ["infractionID", infraction_id])
        except db_error.OperationalError:
            pass

    def mute_user(self, user: int, endtime: int, infractionID: str) -> None:

        try:
            self._db.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])
        except db_error.OperationalError:
            self.create_guild_db()
            self._db.add_to_table(f"{self.guild}_mutes", [["infractionID", infractionID], ["userID", user], ["endMute", endtime]])

    def unmute_user(self, infractionid: Optional[str] = None, userid: Optional[int] = None) -> None:

        try:
            if infractionid is not None:
                self._db.delete_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionid])
            if userid is not None:
                self._db.delete_rows_from_table(f"{self.guild}_mutes", ["userid", userid])
        except db_error.OperationalError:
            pass

    def download_guild_db(self) -> Dict[str, List[List[Union[str, int]]]]:
        """
        Download a guilds database

        This function is pending deprecation till a better solution is coded into an endpoint

        :returns: Dict[str, List[List[Union[str, int]]]] - A json safe export of a guilds tables
        """

        # TODO(ultrabear): deprecate and rewrite this to grab schema from the database, allowing for enums
        dbdict: Dict[str, List[List[Union[str, int]]]] = {
            "config": [["property", "value"]],
            "infractions": [["infractionID", "userID", "moderatorID", "type", "reason", "timestamp"]],
            "mutes": [["infractionID", "userID", "endMute"]],
            "starboard": [["messageID"]]
            }

        for i in ["config", "infractions", "starboard", "mutes"]:
            try:
                dbdict[i].extend(self._db.fetch_table(f"{self.guild}_{i}"))
            except db_error.OperationalError:
                pass

        return dbdict

    def full_download_guild_db(self) -> Dict[str, List[List[Union[str, int]]]]:
        """
        full_download_guild_db downloads an entire database including custom enum tables

        Currently this function just calls download_guild_db() but it is planned to be replaced with a dynamic solution
        New code should use this function so that they dont have to rename their functions later

        :returns: Dict[str, List[List[Union[str, int]]]] - A json safe export of a guilds tables
        """
        return self.download_guild_db()

    def upload_guild_db(self, dbdict: Dict[str, List[List[Any]]]) -> bool:
        """
        Uploads a guilds database from a db hashmap

        If you are uploading a db with custom enums you must inject those enums before uploading
        """

        self.inject_enum("starboard", [
            ("messageID", str),
            ])

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
                    self._db.add_to_table(f"{self.guild}_{i}", tuple(zip(reimport[i][0], row)))
                except db_error.OperationalError:
                    return False

        return True

    def delete_guild_db(self) -> None:

        for i in ["config", "infractions", "starboard", "mutes"]:
            try:
                self._db.delete_table(f"{self.guild}_{i}")
            except db_error.OperationalError:
                pass

    def add_infraction(self, infraction_id: str, user_id: str, moderator_id: str, itype: str, reason: str, timestamp: int, automod: bool = False) -> None:

        quer: Tuple[Tuple[str, Union[str, int]], ...]
        quer = tuple(zip(("infractionID", "userID", "moderatorID", "type", "reason", "timestamp"), (infraction_id, user_id, moderator_id, itype, reason, timestamp)))

        table_name = f"{self.guild}_infractions"

        # TODO(ultrabear): Make all infraction grabbing functions check version and MAINTAIN SAME API
        # New functions need to be coded to get full flags data
        if self._sonnet_db_version >= (1, 1, 0):
            # Tuples have fixed length :cry:
            quer = quer + (("flags", int(automod)), )

        try:
            self._db.add_to_table(table_name, quer)
        except db_error.OperationalError:
            self.create_guild_db()
            self._db.add_to_table(table_name, quer)

    def fetch_all_mutes(self) -> List[Tuple[str, str, str, int]]:

        # Grab list of tables
        tablelist = self._db.list_tables("%_mutes")

        mutetable: List[Tuple[str, str, str, int]] = []
        for i in tablelist:
            mutetable.extend([(i[0][:-6], ) + tuple(a) for a in self._db.fetch_table(i[0])])  # type: ignore[misc]

        return mutetable

    def is_muted(self, userid: Optional[int] = None, infractionid: Optional[str] = None) -> bool:

        try:
            if userid is not None:
                muted = bool(self._db.fetch_rows_from_table(f"{self.guild}_mutes", ["userID", userid]))
            elif infractionid is not None:
                muted = bool(self._db.fetch_rows_from_table(f"{self.guild}_mutes", ["infractionID", infractionid]))
        except db_error.OperationalError:
            muted = False

        return muted

    def close(self) -> None:
        self._db.commit()

    def __exit__(self, err_type: Optional[Type[Exception]], err_value: Optional[str], err_traceback: Any) -> None:
        self._db.commit()
        if err_type:
            raise err_type(err_value)
