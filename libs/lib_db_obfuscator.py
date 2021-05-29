# An Obfuscation layer that handles grabbing sonnet style databases
# Ultrabear 2020

import importlib

import lib_sonnetdb

importlib.reload(lib_sonnetdb)
from lib_sonnetdb import db_hlapi


# make pyflakes shut up
def getdb():
    return db_hlapi
