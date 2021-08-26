# Dynamic loader for sonnet configs
# Ultrabear 2021

import sonnet_cfg

from typing import Any, Type, TypeVar

__all__ = [
    "GLOBAL_PREFIX",
    "BLACKLIST_ACTION",
    "STARBOARD_EMOJI",
    "STARBOARD_COUNT",
    "DB_TYPE",
    "SQLITE3_LOCATION",
    "REGEX_VERSION",
    "CLIB_LOAD",
    "GOLIB_LOAD",
    "GOLIB_VERSION",
    ]

Typ = TypeVar("Typ")


# Loads a config and checks its type
def _load_cfg(attr: str, default: Any, typ: Type[Typ]) -> Typ:

    conf: Any = getattr(sonnet_cfg, attr, default)

    if not isinstance(conf, typ):
        raise TypeError(f"Sonnet Config {attr} is not type {typ.__name__}")

    return conf


GLOBAL_PREFIX = _load_cfg("GLOBAL_PREFIX", "!", str)
BLACKLIST_ACTION = _load_cfg("BLACKLIST_ACTION", "warn", str)
STARBOARD_EMOJI = _load_cfg("STARBOARD_EMOJI", "⭐", str)
STARBOARD_COUNT = _load_cfg("STARBOARD_COUNT", "5", str)
DB_TYPE = _load_cfg("DB_TYPE", "mariadb", str)
SQLITE3_LOCATION = _load_cfg("SQLITE3_LOCATION", "datastore/sonnetdb.db", str)
REGEX_VERSION = _load_cfg("REGEX_VERSION", "re2", str)
CLIB_LOAD = _load_cfg("CLIB_LOAD", True, bool)
GOLIB_LOAD = _load_cfg("GOLIB_LOAD", True, bool)
GOLIB_VERSION = _load_cfg("GOLIB_VERSION", "go", str)
