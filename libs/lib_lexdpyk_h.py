# Headers for the kernel ramfs

import io

from typing import Optional, List, Any, Tuple, Dict, Callable, Coroutine


# Define ramfs headers
class ram_filesystem:
    def mkdir(self, make_dir: str) -> Any:
        pass

    def remove_f(self, remove_item: str) -> None:
        pass

    def read_f(self, file_to_open: str) -> Any:
        pass

    def create_f(self, file_to_write: str, f_type: Optional[type] = io.BytesIO, f_args: Optional[List[Any]] = []) -> Any:
        pass

    def rmdir(self, directory_to_delete: str) -> None:
        pass

    def ls(self, *folderpath: str) -> Tuple[List[str], List[str]]:
        pass

    def tree(self, *folderpath: str) -> Tuple[List[str], Dict[str, Tuple[Any]]]:
        pass


class cmd_module:
    category_info: Dict[str, str]
    commands: Dict[str, Dict[str, Any]]
    version_info: str


cmd_modules_dict = Dict[str, Dict[str, Any]]


class dlib_module:
    category_info: Dict[str, str]
    commands: Dict[str, Callable[..., Coroutine[Any, Any, None]]]
    version_info: str


dlib_modules_dict = Dict[str, Callable[..., Coroutine[Any, Any, None]]]
