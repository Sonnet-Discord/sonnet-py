import sys
import os

sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')

from lib_goparsers import ParseDurationSuper

from typing import Callable, TypeVar, List, Optional, Final, Iterable

T = TypeVar("T")
O = TypeVar("O")


def test_func_io(func: Callable[[T], O], arg: T, expect: O) -> None:
    assert func(arg) == expect, f"func({arg=})={func(arg)} != {expect=}"


def test_parse_duration() -> Optional[Iterable[Exception]]:
    WEEK: Final = 7 * 24 * 60 * 60
    DAY: Final = 24 * 60 * 60
    HOUR: Final = 60 * 60
    MINUTE: Final = 60
    SECOND: Final = 1
    tests = (
        [
            # "Real user" tests, general correctness
            ("123", 123),
            ("5minutes", 5 * MINUTE),
            ("45s", 45),
            ("s", 1),
            # Various rejection paths
            ("5monite", None),
            ("sfgdsgf", None),
            ("minutes5", None),
            ("5seconds4", None),
            ("seconds5m", None),
            ("", None),
            ("josh", None),
            ("seconds5seconds", None),
            ("1w1wday", None),
            ("1day2weeks7dam", None),
            # Test all unit names have correct outputs
            ("1w1week1weeks", 3 * WEEK),
            ("1d1day1days", 3 * DAY),
            ("1h1hour1hours", 3 * HOUR),
            ("1m1minute1minutes", 3 * MINUTE),
            ("1s1second1seconds", 3 * SECOND),
            # Test all single unit cases
            ("week", WEEK),
            ("w", WEEK),
            ("day", DAY),
            ("d", DAY),
            ("hour", HOUR),
            ("h", HOUR),
            ("minute", MINUTE),
            ("m", MINUTE),
            ("second", SECOND),
            ("s", SECOND),
            # Test for floating point accuracy
            (f"{(1<<54)+1}m1s", ((1 << 54) + 1) * 60 + 1),
            ("4.5h", 4 * HOUR + 30 * MINUTE),
            ("4.7h", 4 * HOUR + (7 * HOUR // 10)),
            ("3.5d7.3m", 3 * DAY + 12 * HOUR + 7 * MINUTE + (3 * MINUTE // 10)),
            # Test for fp parse rejection
            ("5.6.34seconds", None),
            ]
        )
    out = []

    for i in tests:
        try:
            test_func_io(ParseDurationSuper, i[0], i[1])
        except AssertionError as e:
            out.append(e)

    if out: return out
    else:
        return None


testfuncs: List[Callable[[], Optional[Iterable[Exception]]]] = [test_parse_duration]


def main_tests() -> None:

    failure = False

    for i in testfuncs:
        errs = i()
        if errs is not None:
            failure = True
            print(i)
            for e in errs:
                print(e)

    if failure:
        sys.exit(1)


if __name__ == "__main__":
    main_tests()
