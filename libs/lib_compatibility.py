# Compatibility patcher for dpy1.7 to (dpy/pyc)2.0
# Handles version changes between the two
# Ultrabear 2021

import discord
import datetime

from typing import Union, cast

releaselevel: int = discord.version_info[0]


class compatErrors:
    class NotFound(Exception):
        pass

    class VersionError(Exception):
        pass


def user_avatar_url(user: Union[discord.User, discord.Member]) -> str:
    """
    Gets the avatar url of a user object
    This is coded in because the behavior changed between 1.7 and 2.0

    :returns: str - The avatar url
    :raises: AttributeError - Failed to get the avatar url (programming error)
    :raises: compatErrors.NotFound - Could not get the avatar url (raised only in 2.0)
    :raises: compatErrors.VersionError - Could not parse library version
    """

    # 1.7: user.avatar_url -> Asset (supports __str__())
    # 2.0: user.avatar.url -> str

    if releaselevel == 1:
        return str(getattr(user, "avatar_url"))
    elif releaselevel == 2:
        avatar = getattr(user, "avatar")
        if avatar is not None:
            # Do a cast here since url is a str already
            return cast(str, getattr(avatar, "url"))
        else:
            raise compatErrors.NotFound(f"Could not find avatar for user {user:r}")
    else:
        raise compatErrors.VersionError("Could not get the library version")


# Returns either an aware or unaware
def discord_datetime_now() -> datetime.datetime:
    """
    Returns either an aware or naive datetime object depending on the dpy version
    This should only be used to check against message.created_at or other dpy passed timestamps
    Timestamps passed to dpy should use lib_loaders.datetime_now to assert unix

    :returns: datetime.datetime - an aware or naive datetime object depending on dpy version
    :raises: compatErrors.VersionError - Could not parse library version
    """

    # 1.7: datetime naive
    # 2.0: datetime aware

    if releaselevel == 1:
        return datetime.datetime.now()
    elif releaselevel == 2:
        return datetime.datetime.now(datetime.timezone.utc)
    else:
        raise compatErrors.VersionError("Could not passe library version")
