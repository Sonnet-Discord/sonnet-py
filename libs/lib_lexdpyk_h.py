# Headers for the kernel ramfs

import io

from typing import Optional, List, Any, Tuple, Dict, Callable, Coroutine, Type, TypeVar, Protocol, overload

Obj = TypeVar("Obj")


# Define ramfs headers
class ram_filesystem(Protocol):
    def mkdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":
        ...

    def remove_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:
        ...

    def read_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:
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
