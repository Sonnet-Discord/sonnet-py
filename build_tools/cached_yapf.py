# multithreaded caching implemented for yapf

import sys
import os
import glob
import argparse
import asyncio
import hashlib
import shutil
import subprocess
from dataclasses import dataclass

from typing import List, Literal, Final, Dict, AsyncIterator


@dataclass
class CachedYapfArgs:
    mode: Literal["diff", "inplace"]
    clear: bool
    directory: str

    @classmethod
    def parse_argparse(cls, args: List[str]) -> "CachedYapfArgs":

        parser = argparse.ArgumentParser(args[0])
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("-d", "--diff", action="store_true", help="run cached_yapf in diff mode over current directory")
        group.add_argument("-i", "--inplace", action="store_true", help="run cached_yapf in inplace overwrite mode over current directory")
        parser.add_argument("-c", "--clear", action="store_true", help="clear cache before running (this is necessary after editing yapf config)")
        parser.add_argument("-D", "--dir", help="run over specified directory instead of current directory")

        parsed = parser.parse_args(args[1:])

        mode: Literal["diff", "inplace"]
        if parsed.diff:
            mode = "diff"
        elif parsed.inplace:
            mode = "inplace"
        else:
            raise RuntimeError("Neither diff or inplace mode specified")

        clear = bool(parsed.clear)

        directory = str(parsed.dir) if parsed.dir is not None else "."

        return cls(mode, clear, directory)


@dataclass
class ProcessedData:
    file: str
    stdout: bytes
    stderr: bytes
    returncode: int


@dataclass
class CacheEntry:
    """
    A entry in the cache, if safe_hash matches a FileCacheEntry hash it is effectively cached
    """
    safe_hash: str
    filename: str

    def to_disk_repr(self) -> str:
        return f"{self.safe_hash} {self.filename}\n"

    @classmethod
    def from_file_cache_entry(cls, entry: "FileCacheEntry") -> "CacheEntry":
        return cls(entry.hashed, entry.filename)


@dataclass
class FileCacheEntry:
    """
    A entry from a raw file and associated hash
    """
    hashed: str
    filename: str

    @classmethod
    def from_file(cls, filename: str) -> "FileCacheEntry":
        """
        Generates a FileCacheEntry from a file
        """

        with open(filename, "rb") as fp:
            hashed = hashlib.sha512(fp.read()).hexdigest()

        return cls(hashed, filename)


CACHED_DIR: Final = "./.cached_yapf"


def get_current_yapf_version(cached: List[str] = []) -> str:
    if cached:
        return cached[0]
    else:
        cached.append(subprocess.run(["yapf", "--version"], capture_output=True).stdout.decode("utf8"))
        return cached[0]


def clear_cache() -> None:
    try:
        shutil.rmtree(CACHED_DIR)
    except FileNotFoundError:
        pass


def load_cache() -> Dict[str, CacheEntry]:

    try:
        with open(f"{CACHED_DIR}/yapf_version", "r", encoding="utf8") as yapf_ver:
            if get_current_yapf_version() != yapf_ver.read():
                return {}
    except FileNotFoundError:
        return {}

    try:
        with open(f"{CACHED_DIR}/cache", "r", encoding="utf8") as cachefile:
            cache = [CacheEntry((v := i.split(" "))[0], v[1].strip("\n")) for i in cachefile if i]
            return {c.filename: c for c in cache}
    except FileNotFoundError:
        return {}


def overwrite_cache(oldcache: Dict[str, CacheEntry], newfiles: List[str]) -> None:

    try:
        os.mkdir(CACHED_DIR)
    except FileExistsError:
        pass

    for i in newfiles:
        oldcache[i] = CacheEntry.from_file_cache_entry(FileCacheEntry.from_file(i))

    with open(f"{CACHED_DIR}/cache", "w+", encoding="utf8") as out:
        for _, c in oldcache.items():
            out.write(c.to_disk_repr())

    with open(f"{CACHED_DIR}/yapf_version", "w+", encoding="utf8") as verfile:
        verfile.write(get_current_yapf_version())


async def run_single_yapf(mode: Literal["diff", "inplace"], filename: str) -> ProcessedData:

    arg = "d" if mode == "diff" else "i"

    proc = await asyncio.create_subprocess_exec("yapf", f"-{arg}", filename, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await proc.communicate()

    return ProcessedData(filename, stdout, stderr, proc.returncode or 0)


async def run_yapf_async(mode: Literal["diff", "inplace"], files: List[str]) -> AsyncIterator[ProcessedData]:
    """
    Runs multiple yapf instances in async subprocesses  and provides returncode and info for each
    """
    tasks = [asyncio.create_task(run_single_yapf(mode, i)) for i in files]
    return (await task for task in tasks)


def run_yapf_once(mode: Literal["diff", "inplace"], files: List[str]) -> "subprocess.CompletedProcess[bytes]":
    """
    Runs one yapf instance over a list of files, providing one ProcessedData instance to represent its output and return code
    """
    arg = "d" if mode == "diff" else "i"
    return subprocess.run(["yapf", f"-{arg}p", *files], capture_output=True)


def process_inplace(cache: Dict[str, CacheEntry], files: List[str]) -> int:

    proc = run_yapf_once("inplace", files)

    if proc.stdout:
        print(proc.stdout.decode("utf8"))
    if proc.stderr:
        print(proc.stderr.decode("utf8"), file=sys.stderr)

    if proc.returncode == 0:
        overwrite_cache(cache, files)

    return proc.returncode


async def process_diff(cache: Dict[str, CacheEntry], files: List[str]) -> int:
    returncode = 0

    safe_cached = []

    async for proc in await run_yapf_async("diff", files):

        if proc.stdout:
            print(proc.stdout.decode("utf8"))
        if proc.stderr:
            print(proc.stderr.decode("utf8"), file=sys.stderr)

        if proc.returncode == 0:
            safe_cached.append(proc.file)
        else:
            returncode = 1

        overwrite_cache(cache, safe_cached)

    return returncode


def main(args: List[str]) -> int:

    parsed = CachedYapfArgs.parse_argparse(args)

    if parsed.clear:
        clear_cache()

    cache = load_cache()

    process = []

    for i in glob.iglob(parsed.directory + "/**/*.py", recursive=True):
        i = str(os.path.abspath(i))
        if i in cache:
            if FileCacheEntry.from_file(i).hashed != cache[i].safe_hash:
                process.append(i)
        else:
            process.append(i)

    if not process:
        return 0

    if parsed.mode == "inplace":
        return process_inplace(cache, process)
    else:
        return asyncio.run(process_diff(cache, process))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
