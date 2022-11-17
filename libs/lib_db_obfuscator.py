# An Obfuscation layer that handles grabbing sonnet style databases
# Ultrabear 2020

# Explicitly export 
__all__ = ["db_hlapi", "DATABASE_FATAL_CONNECTION_LOSS"]

# We now allow connection loss to be handled more gracefully
from lib_sonnetdb import db_hlapi, DATABASE_FATAL_CONNECTION_LOSS
