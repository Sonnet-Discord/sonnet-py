# Command backwards compatible api wrapper that allows new endpoints
# Ultrabear 2021

import inspect
from typing import (Any, Callable, Coroutine, Dict, List, Protocol, Tuple, Union, cast)
from typing_extensions import TypeGuard  # pytype: disable=not-supported-yet

import discord
import lib_lexdpyk_h as lexdpyk


class ExecutableT(Protocol):
    def __call__(self, message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Coroutine[None, None, Any]:
        ...


class ExecutableCtxT(Protocol):
    def __call__(self, message: discord.Message, args: List[str], client: discord.Client, ctx: "CommandCtx") -> Coroutine[None, None, Any]:
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


class CommandCtx:
    __slots__ = "stats", "cmds", "ramfs", "kernel_ramfs", "bot_start", "dlibs", "main_version", "conf_cache", "verbose", "cmds_dict", "automod"

    def __init__(self, kwargdata: Dict[str, Any]) -> None:

        self.stats: Dict[str, int] = kwargdata["stats"]
        self.cmds: List[lexdpyk.cmd_module] = kwargdata["cmds"]
        self.ramfs: lexdpyk.ram_filesystem = kwargdata["ramfs"]
        self.kernel_ramfs: lexdpyk.ram_filesystem = kwargdata["kernel_ramfs"]
        self.bot_start: float = kwargdata["bot_start"]
        self.dlibs: List[lexdpyk.dlib_module] = kwargdata["dlibs"]
        self.main_version: str = kwargdata["main_version"]
        self.conf_cache: Dict[str, Any] = kwargdata["conf_cache"]
        self.verbose: bool = kwargdata["verbose"]
        self.cmds_dict: lexdpyk.cmd_modules_dict = kwargdata["cmds_dict"]
        self.automod: bool = kwargdata["automod"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats": self.stats,
            "cmds": self.cmds,
            "ramfs": self.ramfs,
            "kernel_ramfs": self.kernel_ramfs,
            "bot_start": self.bot_start,
            "dlibs": self.dlibs,
            "main_version": self.main_version,
            "conf_cache": self.conf_cache,
            "verbose": self.verbose,
            "cmds_dict": self.cmds_dict,
            "automod": self.automod,
            }


def _iskwargcallable(func: Union[ExecutableT, ExecutableCtxT]) -> TypeGuard[ExecutableT]:
    spec = inspect.getfullargspec(func)
    return len(spec.args) == 3 and spec.varkw is not None


def CallKwargs(func: Union[ExecutableT, ExecutableCtxT]) -> ExecutableT:
    if _iskwargcallable(func):
        return func
    else:
        # Closures go brr
        def KwargsToCtx(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Coroutine[None, None, Any]:
            ctx = CommandCtx(kwargs)
            return cast(ExecutableCtxT, func)(message, args, client, ctx)

        return KwargsToCtx


def CallCtx(func: Union[ExecutableCtxT, ExecutableT]) -> ExecutableCtxT:
    if _iskwargcallable(func):

        def CtxToKwargs(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Coroutine[None, None, Any]:
            kwargs = ctx.to_dict()
            return func(message, args, client, **kwargs)

        return CtxToKwargs
    else:
        return cast(ExecutableCtxT, func)


class SonnetCommand(dict):  # type: ignore[type-arg]
    __slots__ = ()

    def __getitem__(self, item: Any) -> Any:
        # override execute to return a CallKwargs to maintain backwards compat
        if item == "execute":
            return CallKwargs(super().__getitem__(item))
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
    def execute_kwargs(self) -> ExecutableT:
        return CallKwargs(super().__getitem__("execute"))

    @property
    def execute_ctx(self) -> ExecutableCtxT:
        return CallCtx(super().__getitem__("execute"))

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
