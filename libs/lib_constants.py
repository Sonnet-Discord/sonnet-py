# Constants cause discord likes to troll us
# Ultrabear 2021

from typing import Final  # pytype: disable=import-error


class message:
    __slots__ = ()
    content: Final[int] = 2000


class embed:
    __slots__ = ()

    title: Final[int] = 256
    description: Final[int] = 2048
    author: Final[int] = 256

    class field:
        __slots__ = ()
        name: Final[int] = 256
        value: Final[int] = 1024

    footer: Final[int] = 2048


class sonnet:
    __slots__ = ()

    error_embed: Final[str] = "ERROR: The bot does not have permissions to send embeds here"

    class error_args:
        __slots__ = ()
        not_enough: Final[str] = "ERROR: Not enough args supplied"

    class error_channel:
        __slots__ = ()
        none: Final[str] = "ERROR: No channel supplied"
        invalid: Final[str] = "ERROR: Channel is not a valid channel"
        wrongType: Final[str] = "ERROR: Channel is not the correct type"
        scope: Final[str] = "ERROR: Channel is not in guild"

    class error_role:
        __slots__ = ()
        none: Final[str] = "ERROR: No role supplied"
        invalid: Final[str] = "ERROR: Role is not valid role"

    class error_message:
        __slots__ = ()
        invalid: Final[str] = "ERROR: Message does not exist"
