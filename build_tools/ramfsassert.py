# Tool to test ramfs correctness
# Ultrabear 2021

# imports LeXdPyK, hopefully
# This is jank

import sys
import os

sys.path.insert(1, os.getcwd())

from main import ram_filesystem

from typing import List

testfs = ram_filesystem()


def assertdir(files: List[str], directory: List[str]) -> None:
    assert testfs.ls() == (files, directory)


testfs.mkdir("abcde")

assertdir([], ["abcde"])

testfs.rmdir("abcde")

assertdir([], [])

testfs.create_f("dir/file", f_type=bytes, f_args=[64])

assert isinstance(testfs.read_f("dir/file"), bytes) and len(testfs.read_f("dir/file")) == 64

assertdir([], ["dir"])

testfs.remove_f("dir/file")

assert testfs.ls("dir") == ([], [])

testfs.rmdir("dir")

assertdir([], [])

print("Testing Completed with no errors")
