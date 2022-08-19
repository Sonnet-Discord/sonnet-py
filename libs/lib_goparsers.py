# package lib_goparsers
# - UltraBear 2021

__all__ = [
    "errors",
    "hascompiled",
    "ParseDuration",
    "MustParseDuration",
    "ParseDurationSuper",
    "GenerateCacheFile",
    "GetVersion",
    ]

import importlib

import ctypes as _ctypes
import subprocess as _subprocess
from functools import lru_cache

from typing import Optional

import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)
import lib_datetimeplus

importlib.reload(lib_datetimeplus)

from lib_sonnetconfig import GOLIB_LOAD, GOLIB_VERSION
from lib_datetimeplus import Duration as _Duration


class _GoString(_ctypes.Structure):
    __slots__ = ()
    _fields_ = [("data", _ctypes.c_char_p), ("len", _ctypes.c_int)]


class _ParseDurationRet(_ctypes.Structure):
    __slots__ = ()
    _fields_ = [("ret", _ctypes.c_longlong), ("err", _ctypes.c_int)]


_version = "2.0.0-DEV.3"
_gotools: Optional[_ctypes.CDLL]
if GOLIB_LOAD:
    try:
        _gotools = _ctypes.CDLL(f"./libs/compiled/gotools.{_version}.so")
    except OSError:
        try:
            if _subprocess.run(["make", "gotools", f"GOCMD={GOLIB_VERSION}"]).returncode == 0:
                _gotools = _ctypes.CDLL(f"./libs/compiled/gotools.{_version}.so")
            else:
                _gotools = None
        except OSError:
            _gotools = None
else:
    _gotools = None

hascompiled = _gotools is not None

if _gotools is not None:
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
        __slots__ = ()

    class NoBinaryError(GoParsersError):
        """
        Error stating there is no golang binary to run
        """
        __slots__ = ()

    class ParseFailureError(GoParsersError):
        """
        Error stating there was a failure to parse data for a generic reason
        """
        __slots__ = ()


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

    if _gotools is not None:

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
    Deprecated: use MustParseDuration or ParseDurationSuper
    Parses a Duration from a string using go stdlib

    :raises: errors.NoBinaryError - ctypes could not load the go binary, no parsing occurred
    :raises: errors.ParseFailureError - Failed to parse time
    :returns: int - Time parsed in seconds
    """

    if _gotools is None:
        raise errors.NoBinaryError("ParseDuration: No binary found")

    # Special case to default to seconds
    try:
        return int(s)
    except ValueError:
        pass

    r = _gotools.ParseDuration(_FromString(s))

    if r.err != 0:
        raise errors.ParseFailureError(f"ParseDuration: returned status code {r.err}")

    return int(r.ret // 1000 // 1000 // 1000)


def MustParseDuration(s: str) -> int:
    """
    Parses a Duration from a string using ParseDurationSuper with API similarity to ParseDuration

    :raises: errors.ParseFailureError - Failed to parse time
    :returns: int - Time parsed in seconds
    """

    ret = ParseDurationSuper(s)

    if ret is None:
        raise errors.ParseFailureError("MustParseDuration: pyparser returned error")
    else:
        return ret


@lru_cache(maxsize=500)
def ParseDurationSuper(s: str) -> Optional[int]:
    """
    Parses a duration in pure python
    Where number is a float or float/float fraction
    Allows ({number}{suffix})+ where suffix is weeks|days|hours|minutes|seconds or singular or single char shorthands
    Parses {number} => seconds
    Parses {singular|single char} suffix => 1 of suffix type (day => 1day)

    Numbers are kept as integer values when possible, floating point values are subject to IEEE-754 64 bit limitations.
    Fraction numerators are multiplied by their suffix multiplier before being divided by their denominator, with floating point math starting where the first float is present

    :returns: Optional[int] - Return value, None if it could not be parsed
    """

    # Call into Duration.parse, replaces codebase of ParseDurationSuper
    if (v := _Duration.parse(s)) is not None:
        return v.seconds()
    else:
        return None
