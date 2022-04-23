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
from dataclasses import dataclass
import string

from typing import Optional, Dict, NamedTuple, List, Literal, Set, Any

import lib_sonnetconfig

importlib.reload(lib_sonnetconfig)

from lib_sonnetconfig import GOLIB_LOAD, GOLIB_VERSION


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


_super_table: Dict[str, int] = {
    "week": 60 * 60 * 24 * 7,
    "w": 60 * 60 * 24 * 7,
    "day": 60 * 60 * 24,
    "d": 60 * 60 * 24,
    "hour": 60 * 60,
    "h": 60 * 60,
    "minute": 60,
    "m": 60,
    "second": 1,
    "s": 1,
    }

_suffix_table: Dict[str, int] = dict([("weeks", 60 * 60 * 24 * 7), ("days", 60 * 60 * 24), ("hours", 60 * 60), ("minutes", 60), ("seconds", 1)] + list(_super_table.items()))

_alpha_chars = set(char for word in _suffix_table for char in word)
_digit_chars = set(string.digits + ".")
_allowed_chars: Set[str] = _alpha_chars.union(_digit_chars)


class _SuffixedNumber(NamedTuple):
    number: float
    suffix: str


@dataclass
class _TypedStr:
    __slots__ = "s", "t"
    s: str
    t: Literal["digit", "suffix"]


class _idx_ptr:
    __slots__ = "idx",

    def __init__(self, idx: int):
        self.idx = idx

    def inc(self) -> "_idx_ptr":
        self.idx += 1
        return self

    def __enter__(self) -> "_idx_ptr":
        return self

    def __exit__(self, *ignore: Any) -> None:
        self.idx += 1


def _str_to_tree(s: str) -> Optional[List[_SuffixedNumber]]:

    tree: List[_TypedStr] = []

    idx = _idx_ptr(0)

    while idx.idx < len(s):
        with idx:
            if s[idx.idx] in _digit_chars:
                cache = [s[idx.idx]]
                while len(s) > idx.idx + 1 and s[idx.idx + 1] in _digit_chars:
                    cache.append(s[idx.inc().idx])

                tree.append(_TypedStr("".join(cache), "digit"))
            elif s[idx.idx] in _alpha_chars:

                cache = [s[idx.idx]]
                while len(s) > idx.idx + 1 and s[idx.idx + 1] in _alpha_chars:
                    cache.append(s[idx.inc().idx])

                tree.append(_TypedStr("".join(cache), "suffix"))

            else:
                return None

    if not tree:
        return None

    if len(tree) == 1:
        if tree[0].t == "digit":
            try:
                if "." in tree[0].s:
                    return [_SuffixedNumber(float(tree[0].s), "s")]
                else:
                    return [_SuffixedNumber(int(tree[0].s), "s")]
            except ValueError:
                return None
        else:
            return None

    # assert len(tree) > 1

    # Cant start on a suffix
    if tree[0].t == "suffix":
        return None

    if tree[-1].t == "digit":
        return None

    # Assert that lengths are correct, should be asserted by previous logic
    if not len(tree) % 2 == 0:
        return None

    out: List[_SuffixedNumber] = []

    # alternating digit and suffix starting with digit and ending on suffix
    for i in range(0, len(tree), 2):
        try:
            if '.' in tree[i].s:
                digit = float(tree[i].s)
            else:
                digit = int(tree[i].s)
        except ValueError:
            return None

        if tree[i + 1].s not in _suffix_table:
            return None

        out.append(_SuffixedNumber(digit, tree[i + 1].s))

    return out


def ParseDurationSuper(s: str) -> Optional[int]:
    """
    Parses a duration in pure python
    Allows ({float}{suffix})+ where suffix is weeks|days|hours|minutes|seconds or singular or single char shorthands
    Parses {float} => seconds
    Parses {singular|single char} suffix => 1 of suffix type (day => 1day)

    :returns: Optional[int] - Return value, None if it could not be parsed
    """

    # Check if in supertable
    try:
        return _super_table[s]
    except KeyError:
        pass

    # Quick reject anything not in allowed set
    if not all(ch in _allowed_chars for ch in s):
        return None

    tree = _str_to_tree(s)

    if tree is None: return None

    out = 0

    for i in tree:
        try:
            out += int(i.number * _suffix_table[i.suffix])
        except ValueError:
            return None

    return out
