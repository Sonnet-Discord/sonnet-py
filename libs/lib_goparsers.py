# package lib_goparsers
# - UltraBear 2021

__all__ = [
    "errors",
    "hascompiled",
    "ParseDuration",
    "MustParseDuration",
    "GenerateCacheFile",
    "GetVersion",
    ]

import importlib

import ctypes as _ctypes
import subprocess as _subprocess

from typing import cast

import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)

from lib_sonnetconfig import GOLIB_LOAD


class _GoString(_ctypes.Structure):
    _fields_ = [("data", _ctypes.c_char_p), ("len", _ctypes.c_int)]


class _ParseDurationRet(_ctypes.Structure):
    _fields_ = [("ret", _ctypes.c_longlong), ("err", _ctypes.c_int)]


hascompiled = True
_version = "2.0.0-DEV.3"
if GOLIB_LOAD:
    try:
        _gotools = _ctypes.CDLL(f"./libs/compiled/gotools.{_version}.so")
    except OSError:
        try:
            if _subprocess.run(["make", "gotools"]).returncode == 0:
                _gotools = _ctypes.CDLL(f"./libs/compiled/gotools.{_version}.so")
            else:
                hascompiled = False
        except OSError:
            hascompiled = False
else:
    hascompiled = False

if hascompiled:
    _gotools.ParseDuration.argtypes = [_GoString]
    _gotools.ParseDuration.restype = _ParseDurationRet
    _gotools.GenerateCacheFile.argtypes = [_GoString, _GoString]
    _gotools.GenerateCacheFile.restype = _ctypes.c_int


class errors:
    """
    Errors class for goparsers
    """
    class GoParsersError(Exception):
        """
        Generic error for the goparsers lib, parse related errors should subclass from this
        """
        pass

    class NoBinaryError(GoParsersError):
        """
        Error stating there is no golang binary to run
        """
        pass

    class ParseFailureError(GoParsersError):
        """
        Error stating there was a failure to parse data for a generic reason
        """
        pass


def _FromString(s: str) -> _GoString:
    """
    Returns a GoString from a pystring object
    """
    byte = s.encode("utf8")
    return _GoString(byte, len(byte))


def GetVersion() -> str:
    """
    Returns goparsers underlying version string

    :Returns: str - goparsers version
    """
    return _version


def GenerateCacheFile(fin: str, fout: str) -> None:
    """
    Generates a sonnet wordlist cache file using a go library
    Fallsback to python version if golib is not compiled, aprox 10x slower, but more flexible due to not validating data to be faster

    :raises: errors.ParseFailureError - goparser returned an error, probably io related
    :raises: FileNotFoundError - infile does not exist
    """

    if hascompiled:

        ret = _gotools.GenerateCacheFile(_FromString(fin), _FromString(fout))

        if ret == 1:
            raise errors.ParseFailureError("parser returned error")
        elif ret == 2:
            raise FileNotFoundError(f"No file {fin}")

    else:

        with open(fin, "rb") as words:
            maxval = 0
            structured_data = []
            for byte in words.read().split(b"\n"):
                if byte and not len(byte) > 85 and not b"\xc3" in byte:

                    stv = byte.rstrip(b"\r").decode("utf8")
                    byte = (stv[0].upper() + stv[1:].lower()).encode("utf8")

                    structured_data.append(bytes([len(byte)]) + byte)
                    if len(byte) + 1 > maxval:
                        maxval = len(byte) + 1
        with open(fout, "wb") as structured_data_file:
            structured_data_file.write(bytes([maxval]))
            for byte in structured_data:
                structured_data_file.write(byte + bytes(maxval - len(byte)))


def ParseDuration(s: str) -> int:
    """
    Parses a Duration from a string using go stdlib

    :raises: errors.NoBinaryError - ctypes could not load the go binary, no parsing occured
    :raises: errors.ParseFailureError - Failed to parse time
    :returns: int - Time parsed in seconds
    """

    if not hascompiled:
        raise errors.NoBinaryError("ParseDuration: No binary found")

    # Special case to default to seconds
    try:
        return int(s)
    except ValueError:
        pass

    r = _gotools.ParseDuration(_FromString(s))

    if r.err != 0:
        raise errors.ParseFailureError(f"ParseDuration: returned status code {r.err}")

    return cast(int, r.ret // 1000 // 1000 // 1000)


def MustParseDuration(s: str) -> int:
    """
    Parses a Duration from a string using go stdlib, and fallsback to inferior python version if it does not exist

    Most situations should call this over ParseDuration, unless you want to
    assert whether the golib exists or not, or avoid parsing in python entirely

    :raises: errors.ParseFailureError - Failed to parse time
    :returns: int - Time parsed in seconds
    """

    if hascompiled:

        return ParseDuration(s)

    else:

        try:
            if s[-1] in (multi := {"s": 1, "m": 60, "h": 3600}):
                return int(s[:-1]) * multi[s[-1]]
            else:
                return int(s)
        except (ValueError, TypeError):
            raise errors.ParseFailureError("MustParseDuration: pyparser returned error")
