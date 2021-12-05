# Command backwards compatible api wrapper that allows new endpoints
# Ultrabear 2021

import discord

from typing import Any, List, Callable, Coroutine, Union, Tuple, Protocol, cast


class ExecutableT(Protocol):
    def __call__(self, message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Coroutine[None, None, Any]:
        ...


PermissionT = Union[str, Tuple[str, Callable[[discord.Message], bool]]]

_allowpool = {
    "cache": "keep",
    "permission": "everyone",
    }


class CommandError(Exception):
    """
    CommandError is an error that can be raised by a command

    It is treated specially by the exception handler such that it
    will print the error string to the current channel instead of raising to the kernel, and have the same effect as return != 1
    it should be used for cleaner user error handling

`   `await message.channel.send("error"); return 1`
    may be replaced with
    `raise CommandError("error")`
    for the same effect
    """
    __slots__ = ()


class SonnetCommand(dict):  # type: ignore[type-arg]
    __slots__ = ()

    def __getitem__(self, item: Any) -> Any:
        try:
            return super().__getitem__(item)
        except KeyError:
            return _allowpool[item]

    def get(self, item: Any, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def __contains__(self, item: Any) -> bool:
        if item in _allowpool:
            return True
        else:
            return super().__contains__(item)

    @property
    def execute(self) -> ExecutableT:
        return cast(ExecutableT, self["execute"])

    @property
    def cache(self) -> str:
        return cast(str, self["cache"])

    @property
    def permission(self) -> PermissionT:
        return cast(PermissionT, self["permission"])

    @property
    def description(self) -> str:
        return cast(str, self["description"])

    @property
    def pretty_name(self) -> str:
        return cast(str, self["pretty_name"])

    @property
    def rich_description(self) -> str:
        return cast(str, self["rich_description"])
