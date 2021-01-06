# An Obfuscation layer that handles grabbing rhea or sonnet style databases
# Ultrabear 2020

import importlib

from sonnet_cfg import DB_TYPE, SQLITE3_TYPE

if DB_TYPE == "mariadb":
    import lib_sonnetdb; importlib.reload(lib_sonnetdb)
    from lib_sonnetdb import db_hlapi
elif DB_TYPE == "sqlite3":
    if SQLITE3_TYPE == "sonnet":
        import lib_sonnetdb; importlib.reload(lib_sonnetdb)
        from lib_sonnetdb import db_hlapi
    elif SQLITE3_TYPE == "rhea":
        raise TypeError("Sonnet does not support running on rhea type databases")
