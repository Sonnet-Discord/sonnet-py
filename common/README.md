# List of sonnet\_cfg configs
- `GLOBAL_PREFIX: str` global default prefix of the bot
- `BLACKLIST_ACTION: str` default action on a blacklist break, must be warn,mute,kick,ban
- `STARBOARD_EMOJI: str` default starboard emoji
- `STARBOARD_COUNT: str` default starboard count
- `DB_TYPE: str` db type to use, currently must be either mariadb or sqlite3
- `SQLITE3_LOCATION: str` filepath to sqlite3 db, if selected
- `REGEX_VERSION: str` regex version to use, must be either re2 or re, and re2 must be installed if so
- `CLIB_LOAD: bool` whether to compile and load the clib or not
- `GOLIB_LOAD: bool` whether to compile and load the golib or not
