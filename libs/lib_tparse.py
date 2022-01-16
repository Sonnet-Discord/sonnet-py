# Typed argument parsing library for sonnet (or the world idk)
# Ultrabear 2022

import sys
from dataclasses import dataclass

# Python types
from typing import List, Dict, Tuple, Type
# Predefined types
from typing import Optional, Iterator, Sequence, Callable
# Constructs
from typing import Any, Generic, Protocol, TypeVar, Union, Literal, overload

__all__ = [
    "StringWriter",
    "TParseError",
    "NotParsedError",
    "ParseFailureError",
    "Promise",
    "Parser",
    "store_true",
    "store_false",
    "add_true_false_flag",
    ]


class StringWriter(Protocol):
    """
    A StringWriter is an interface for any object (T) containing a T.write(s: str) -> int method
    """
    def write(self, s: str) -> int:
        ...


class TParseError(Exception):
    """
    An exception that is the BaseException of the tparse library
    """
    __slots__ = ()


class NotParsedError(TParseError):
    """
    NotParsedError is raised when a Promises value is attempted to be gotten without having been parsed
    """
    __slots__ = ()


class ParseFailureError(TParseError):
    """
    ParseFailureError is raised when Parser.parse() fails to parse arguments and exit_on_fail is set to False
    """
    __slots__ = ()


# Promise Type
_PT = TypeVar("_PT")
# Parser Argument Type
_PAT = TypeVar("_PAT")
# Parser Type
_ParserT = TypeVar("_ParserT")
# C Iterator Type
_CIT = TypeVar("_CIT")


class _IteratorCtx:
    __slots__ = "i",

    def __init__(self) -> None:
        self.i = -1


class _CIterator(Generic[_CIT]):
    """
    CIterator is a closer to C style for loop, allowing (i = 0; i < len(T); i++) where i is mutable
    """
    __slots__ = "_sequence", "_state"

    def __init__(self, iterator: Sequence[_CIT]) -> None:
        self._sequence = iterator
        self._state = _IteratorCtx()

    def __iter__(self) -> Iterator[Tuple[_IteratorCtx, _CIT]]:
        return self

    def __next__(self) -> Tuple[_IteratorCtx, _CIT]:
        self._state.i += 1

        if self._state.i >= len(self._sequence):
            raise StopIteration

        return self._state, self._sequence[self._state.i]


class Promise(Generic[_PT]):
    """
    A Promise is similar to the concept of an async promise,
    an argument will be in the promise after parsing has completed,
    but attempting to look before parsing has completed will error.

    As such the argument parser returns typed promise objects per argument that will return data once it has completed parsing, but not before.
    You may also construct a Promise directly with Promise[T]() or with Promise(T) for py3.8 users, and pass it to add_arg(store=) to parse to for multi argument parsing.
    Correct typing is not gauranteed at runtime, but by mypy type checking, code that fails mypy type checking will produce unpredictable runtime behavior.
    """
    __slots__ = "_parsed", "_data"

    def __init__(self, typ: Optional[Type[_PT]] = None) -> None:
        self._parsed: bool = False
        self._data: Optional[_PT] = None

    @overload
    def get(self, default: _PT) -> _PT:
        ...

    @overload
    def get(self, default: Optional[_PT] = None) -> Optional[_PT]:
        ...

    def get(self, default: Optional[_PT] = None) -> Optional[_PT]:
        if not self._parsed:
            raise NotParsedError("This promised argument has not been parsed")
        # Default override
        return default if self._data is None else self._data


# Dataclasses go brr
@dataclass
class _ParserArgument(Generic[_PAT]):
    __slots__ = "names", "func", "flag", "store", "helpstr"
    names: Union[str, List[str]]
    func: Callable[[str], _PAT]
    flag: bool
    store: Promise[_PAT]
    helpstr: Optional[str]


class Parser:
    """
    Parser is the core of the argument parsing library, it facilitates parsing arguments and making good on promises
    """
    __slots__ = "_arguments", "_arghash", "_name", "_buildhelp"

    def __init__(self, name: str = sys.argv[0], buildhelp: bool = False) -> None:

        self._arguments: List[_ParserArgument[Any]] = []
        self._arghash: Dict[str, _ParserArgument[Any]] = {}
        self._name = name
        self._buildhelp = buildhelp
        # TODO(ultrabear): yeah put this in lmfao
        if buildhelp is True: raise NotImplementedError("Help building is not yet implemented")

    def add_arg(
        self,
        names: Union[List[str], str],
        func: Callable[[str], _ParserT],
        flag: bool = False,
        store: Optional[Promise[_ParserT]] = None,
        helpstr: Optional[str] = None,
        ) -> Promise[_ParserT]:
        """add_arg returns a Promise for a passed argument and stores it internally for parsing"""

        if store is None:
            store = Promise()

        # Pointers are fun
        arg = _ParserArgument(names, func, flag, store, helpstr)

        self._arguments.append(arg)

        # Put all names into argument hashmap pointing to same arg for fast lookup
        if isinstance(names, str):
            self._arghash[names] = arg
        else:
            for name in names:
                self._arghash[name] = arg

        return store

    def _error(self, errstr: str, exit_on_fail: bool, stderr: StringWriter) -> None:

        stderr.write(errstr)
        stderr.write("\n")

        if exit_on_fail:
            sys.exit(1)
        else:
            raise ParseFailureError(errstr)

    def parse(self, args: List[str] = sys.argv[1:], stderr: StringWriter = sys.stderr, exit_on_fail: bool = True, lazy: bool = False, consume: bool = False) -> None:
        """
        parse will parse either given args or sys.argv and output errors to stderr or a given StringWriter, exiting or raising an exception based on exit_on_fail
        lazy defines whether or not the parser will ignore garbage arguments
        """

        garbage: List[int] = []

        for idx, val in _CIterator(args):
            if val in self._arghash:
                garbage.append(idx.i)
                arg = self._arghash[val]

                if arg.flag is True:
                    arg.store._data = arg.func("")
                else:
                    idx.i += 1
                    garbage.append(idx.i)
                    if idx.i >= len(args):
                        self._error(f"Failure to parse argument {val}, expected parameter, reached EOL", exit_on_fail, stderr)

                    try:
                        arg.store._data = arg.func(args[idx.i])
                    except ValueError as ve:
                        self._error(f"Failed to parse argument {val}; ValueError: {ve}", exit_on_fail, stderr)

            elif not lazy:
                self._error("Recieved garbage argument", exit_on_fail, stderr)

        if consume:
            garbage.reverse()
            for di in garbage:
                del args[di]

        for i in self._arguments:
            i.store._parsed = True


def store_true(s: str) -> Literal[True]:
    """Returns true when called, can be used as func for add_arg flagtypes"""
    return True


def store_false(s: str) -> Literal[False]:
    """Returns false when called, can be used as func for add_arg flagtypes"""
    return False


def add_true_false_flag(p: Parser, name: str) -> Promise[bool]:

    pr = Promise(bool)

    p.add_arg(f"--{name}", store_true, flag=True, store=pr)
    p.add_arg(f"--no-{name}", store_false, flag=True, store=pr)

    return pr
