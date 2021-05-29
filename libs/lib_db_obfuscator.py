# An Obfuscation layer that handles grabbing sonnet style databases
# Ultrabear 2020

import importlib

import libs.lib_sonnetdb

importlib.reload(libs.lib_sonnetdb)
from libs.lib_sonnetdb import db_hlapi


# make pyflakes shut up
def getdb():
    return db_hlapi
