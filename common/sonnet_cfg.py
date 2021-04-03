# Configuration File

# Default global prefix, can be set per server
GLOBAL_PREFIX = '!'
# Default action to occur when someone breaks blacklist, can be set per server
BLACKLIST_ACTION = "warn"
# Default emoji to use for starboard, can be set per server
STARBOARD_EMOJI = "⭐"
# Default starboard reaction threshhold, can be set per server
STARBOARD_COUNT = "5"

# chose between using mariadb or sqlite3
DB_TYPE = "mariadb"
# only needs to be set if using sqlite3 db in sonnet mode, mariadb login is stored in .login-info.txt
SQLITE3_LOCATION = "datastore/sonnetdb.db"

# Configure whether to use re2 or re, any public instance must use re2 due to exploits, however re is cross platform and easier to set up
REGEX_VERSION = "re2"

# Configure whether or not to load the C loader
CLIB_LOAD = True
