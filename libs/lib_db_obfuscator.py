# An Obfuscation layer that handles grabbing sonnet style databases
# Ultrabear 2020

# Explicitly export db_hlapi
__all__ = [
    "db_hlapi"
]

import importlib

import lib_sonnetdb

importlib.reload(lib_sonnetdb)
from lib_sonnetdb import db_hlapi
