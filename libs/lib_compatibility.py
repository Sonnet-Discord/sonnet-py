# Compatibility patcher for dpy1.7 to (dpy/pyc)2.0
# Handles version changes between the two
# Ultrabear 2021

import discord
import datetime

from typing import Union, Dict, Callable, Protocol, cast
from typing_extensions import TypeGuard

_releaselevel: int = discord.version_info[0]

__all__ = [
    "compatErrors",
    "user_avatar_url",
    "default_avatar_url",
    "has_default_avatar",
    "discord_datetime_now",
    "to_snowflake",
    "GuildMessageable",
    "is_guild_messageable",
    ]


class compatErrors:
    __slots__ = ()

    class NotFound(Exception):
        __slots__ = ()

    class VersionError(Exception):
        __slots__ = ()


_avatar_url_funcs: Dict[int, Callable[[Union[discord.User, discord.Member]], str]] = {
    # 1.0: User.avatar_url
    1: (lambda user: str(getattr(user, "avatar_url"))),
    # 2.0: User.display_avatar.url
    2: (lambda user: cast(str, getattr(getattr(user, "display_avatar"), "url"))),
    }

_default_avatar_url_funcs: Dict[int, Callable[[Union[discord.User, discord.Member]], str]] = {
    # 1.0: User.default_avatar_url
    1: (lambda user: str(getattr(user, "default_avatar_url"))),
    # 2.0: User.default_avatar.url
    2: (lambda user: cast(str, getattr(getattr(user, "default_avatar"), "url"))),
    }

_datetime_now_funcs: Dict[int, Callable[[], datetime.datetime]] = {
    # 1.0: naive datetime
    1: (lambda: datetime.datetime.utcnow()),
    # 2.0: aware datetime
    2: (lambda: datetime.datetime.now(datetime.timezone.utc)),
    }

if _releaselevel in [1, 2]:
    _avatar_url_func = _avatar_url_funcs[_releaselevel]
    _default_avatar_url_func = _default_avatar_url_funcs[_releaselevel]
    _datetime_now_func = _datetime_now_funcs[_releaselevel]
else:
    raise compatErrors.VersionError("Could not get the library version")


def user_avatar_url(user: Union[discord.User, discord.Member]) -> str:
    """
    Gets the avatar url of a user object
    This is coded in because the behavior changed between 1.7 and 2.0

    :returns: str - The avatar url
    :raises: AttributeError - Failed to get the avatar url (programming error)
    """

    # 1.7: user.avatar_url -> Asset (supports __str__())
    # 2.0: user.display_avatar.url -> str

    return user.display_avatar.url


def default_avatar_url(user: Union[discord.User, discord.Member]) -> str:
    """
    Gets the default avatar url of a user object
    This is coded in because User.default_avatar_url is replaced with User.default_avatar.url in 2.0

    :returns: str - The avatar url
    :raises: AttributeError - Failed to get the avatar url (programming error)
    """

    return user.default_avatar.url


def has_default_avatar(user: Union[discord.User, discord.Member]) -> bool:
    """
    Returns if a user has a default avatar
    This function is provided as convenience as 2.0 introduces a better way to test this

    :returns: bool - if the user has a default avatar
    """

    return user.avatar is None


# Returns either an aware or unaware
def discord_datetime_now() -> datetime.datetime:
    """
    Returns either an aware or naive datetime object depending on the dpy version
    This should only be used to check against message.created_at or other dpy passed timestamps
    Timestamps passed to dpy should use lib_loaders.datetime_now to assert unix

    :returns: datetime.datetime - an aware or naive datetime object depending on dpy version
    """

    # 1.7: datetime naive
    # 2.0: datetime aware

    return datetime.datetime.now(datetime.timezone.utc)


class _WeakSnowflake(Protocol):
    id: int


def to_snowflake(v: _WeakSnowflake, /) -> discord.abc.Snowflake:
    """
    Casts any true compatible type into a discord.py Showflake interface, bypassing a interface bug with mypy
    """
    # FIXME(ultrabear):
    # we ignore interface errors here because dpy/mypy 2.0 has a bug where snowflakes interface includes slots
    # when this bug is patched mypy should raise an error for unused type ignores and this should be patched
    return v  # type: ignore[return-value]


GuildMessageable = Union[discord.TextChannel, discord.Thread]

_concrete_channels = Union[discord.TextChannel, discord.VoiceChannel, discord.CategoryChannel, discord.StageChannel, discord.ForumChannel, discord.Thread, discord.DMChannel, discord.GroupChannel,
                           discord.PartialMessageable]
_abstract_base_class_channels = Union[discord.abc.PrivateChannel, discord.abc.GuildChannel]


def is_guild_messageable(v: Union[_concrete_channels, _abstract_base_class_channels], /) -> TypeGuard[GuildMessageable]:
    """
    Returns True if the channel type passed is within a guild and messageable
    """

    return isinstance(v, (discord.TextChannel, discord.Thread))
