# Constants cause discord likes to troll us
# Ultrabear 2021

from typing import Final, Dict  # pytype: disable=import-error


class permission:
    __slots__ = ()
    # manually wrote this
    # hate
    name_offsets: Final[Dict[int, str]] = {
        0: "create instant invite",
        1: "kick members",
        2: "ban members",
        3: "administrator",
        4: "manage channels",
        5: "manage server",
        6: "add reactions",
        7: "view audit log",
        8: "priority speaker",
        9: "video",
        10: "read messages/view channels",
        11: "send messages",
        12: "send tts message",
        13: "manage messages",
        14: "embed links",
        15: "attach files",
        16: "read message history",
        17: "mention everyone",
        18: "use external emojis",
        19: "view server insights",
        20: "connect",
        21: "speak",
        22: "mute members",
        23: "deafen members",
        24: "move members",
        25: "use voice activity",
        26: "change nickname",
        27: "manage nicknames",
        28: "manage roles",
        29: "manage webhooks",
        30: "manage emojis and stickers",
        31: "use slash commands",
        32: "request to speak",  # NOTE(ultrabear) this is listed as 'may be removed'
        33: "manage events",
        34: "manage threads",
        35: "create public threads",
        36: "create private threads",
        37: "use external stickers",
        38: "send messages in threads",
        39: "use activities",
        40: "moderate members",
        }


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
