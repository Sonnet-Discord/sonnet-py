# package lib_goparsers
# - UltraBear 2021

import ctypes as _ctypes
import os

from typing import cast

from sonnet_cfg import CLIB_LOAD


class _GoString(_ctypes.Structure):
    _fields_ = [("data", _ctypes.c_char_p), ("len", _ctypes.c_int)]


class _ParseDurationRet(_ctypes.Structure):
    _fields_ = [("ret", _ctypes.c_longlong), ("err", _ctypes.c_int)]


hascompiled = True
if CLIB_LOAD:
    try:
        _gotools = _ctypes.CDLL("./libs/compiled/gotools.2.0.0-DEV.0.so")
    except OSError:
        try:
            os.system("make gotools")
            _gotools = _ctypes.CDLL("./libs/compiled/gotools.2.0.0-DEV.0.so")
        except OSError:
            hascompiled = False
else:
    hascompiled = False

if hascompiled:
    _gotools.ParseDuration.argtypes = [_GoString]
    _gotools.ParseDuration.restype = _ParseDurationRet


class errors:
    class GoParsersError(Exception):
        pass

    class NoBinaryError(GoParsersError):
        pass

    class ParseFailureError(GoParsersError):
        pass


def ParseDuration(s: str) -> int:
    """
    Parses a Duration from a string using go stdlib

    :raises: errors.NoBinaryError - ctypes could not load the go binary, no parsing occured
    :raises: errors.ParseFailureError - Failed to parse time
    :returns: int - Time parsed in seconds
    """

    if not hascompiled:
        raise errors.NoBinaryError("ParseDuration: No binary found")

    byte = s.encode("utf8")

    r = _gotools.ParseDuration(_GoString(byte, len(byte)))

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
