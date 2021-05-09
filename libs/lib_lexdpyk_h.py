# Headers for the kernel ramfs

import io

from typing import Optional, List, Any

# Define ramfs
class ram_filesystem:
    def mkdir(self, make_dir: str) -> Any:
        return None

    def remove_f(self, remove_item: str) -> None:
        return None

    def read_f(self, file_to_open: str) -> Any:
        return None

    def create_f(self, file_to_write: str, f_type: Optional[type] = io.BytesIO, f_args: Optional[List[Any]] = []) -> Any:
        return None

    def rmdir(self, directory_to_delete: str) -> None:
        return None

    def ls(self, *folderpath: str) -> Any:
        return None

    def tree(self, *folderpath: str) -> Any:
        return None
