# Headers for the kernel ramfs

from typing import Optional, List, Any, Tuple, Dict, Callable, Coroutine, Type, TypeVar

Obj = TypeVar("Obj")


# Define ramfs headers
class ram_filesystem:
    # pytype: disable=bad-return-type
    def mkdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> "ram_filesystem":
        ...

    def remove_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:
        ...

    def read_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Any:
        ...

    def create_f(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None, f_type: Optional[Type[Obj]] = None, f_args: Optional[List[Any]] = None) -> Obj:
        ...

    def rmdir(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> None:
        ...

    def ls(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Tuple[List[str], List[str]]:
        ...

    def tree(self, dirstr: Optional[str] = None, dirlist: Optional[List[str]] = None) -> Tuple[List[str], Dict[str, Tuple[Any]]]:
        ...
    # pytype: enable=bad-return-type


class cmd_module:
    __name__: str
    category_info: Dict[str, str]
    commands: Dict[str, Dict[str, Any]]
    version_info: str


cmd_modules_dict = Dict[str, Dict[str, Any]]


class dlib_module:
    __name__: str
    category_info: Dict[str, str]
    commands: Dict[str, Callable[..., Coroutine[Any, Any, None]]]
    version_info: str


dlib_modules_dict = Dict[str, Callable[..., Coroutine[Any, Any, None]]]
