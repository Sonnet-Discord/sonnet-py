# Headers for the kernel ramfs

import io
import discord
from dataclasses import dataclass

from typing import Optional, List, Any, Tuple, Dict, Callable, Coroutine, Type, TypeVar, Protocol, overload, Set, Union

Obj = TypeVar("Obj")


# Define ramfs headers
class ram_filesystem(Protocol):
    def mkdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":
        ...

    def remove_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:
        ...

    def read_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> object:
        ...

    # pytype: disable=not-callable
    @overload
    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> io.BytesIO:
        ...

    @overload
    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Callable[[Any], Obj]] = None, f_args: Optional[List[Any]] = None) -> Obj:
        ...

    @overload
    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Callable[[], Obj]] = None) -> Obj:
        ...

    @overload
    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Type[Obj]] = None, f_args: Optional[List[Any]] = None) -> Obj:
        ...

    # pytype: enable=not-callable
    def rmdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:
        ...

    def ls(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
        ...

    def tree(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Tuple[List[str], Dict[str, Tuple[Any]]]:
        ...


class cmd_module(Protocol):
    __name__: str
    category_info: Dict[str, str]
    commands: Dict[str, Dict[str, Any]]
    version_info: str


cmd_modules_dict = Dict[str, Dict[str, Any]]


class dlib_module(Protocol):
    __name__: str
    category_info: Dict[str, str]
    commands: Dict[str, Callable[..., Coroutine[Any, Any, None]]]
    version_info: str


dlib_modules_dict = Dict[str, Callable[..., Coroutine[Any, Any, None]]]


@dataclass
class KernelArgs:
    """
    A wrapper around a kernels passed kwargs
    """
    __slots__ = "kernel_version", "bot_start", "client", "ramfs", "kernel_ramfs", "command_modules", "dynamiclib_modules"
    kernel_version: str
    bot_start: float
    client: discord.Client
    ramfs: ram_filesystem
    kernel_ramfs: ram_filesystem
    command_modules: Tuple[List[cmd_module], cmd_modules_dict]
    dynamiclib_modules: Tuple[List[dlib_module], dlib_modules_dict]


_FuncType = Callable[..., Coroutine[Any, Any, Any]]


def ToKernelArgs(f: _FuncType) -> _FuncType:
    """
    A decorator to convert kwargs to KernelArgs for a kernel event handler
    """
    def newfunc(*args: Any, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        nargs = (*args, KernelArgs(**kwargs))
        return f(*nargs)

    return newfunc


class _BotOwners:
    __slots__ = "owners",

    def __init__(self, unknown: Union[List[Union[str, int]], Tuple[Union[str, int], ...], str, int]) -> None:

        self.owners: Set[int]

        if isinstance(unknown, (int, str)):
            self.owners = set([int(unknown)]) if unknown else set()
        else:
            self.owners = set(map(int, unknown))

    def is_owner(self, user: Union[discord.User, discord.Member]) -> bool:
        """
        Returns True if user passed is a bot owner
        """
        return user.id in self.owners

    def get_owners(self) -> List[int]:
        """
        Returns a list of registered bot owners
        This list may be empty
        """
        return list(self.owners)


import LeXdPyK_conf

BotOwners = _BotOwners(LeXdPyK_conf.BOT_OWNER)
