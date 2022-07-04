# A nice time api?
# constructed based off of the idea that datetime is a sound library with a bad api, uses datetime primitives internally but provides a simpler api
# Ultrabear 2022

import datetime
import time
import copy as pycopy
from dataclasses import dataclass
import string

from typing import Optional, Final, List, Any, Union, Literal, Set, Dict

__all__ = [
    "Time",
    "Clock",
    "Date",
    "Duration",
    ]

_NANOS_PER_SECOND: Final = 1000 * 1000 * 1000
_NANOS_PER_MILLI: Final = 1000 * 1000
_NANOS_PER_MICRO: Final = 1000

# parse method data
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
_digit_chars = set(string.digits + "./")
_allowed_chars: Set[str] = _alpha_chars.union(_digit_chars)


@dataclass
class _Fraction:
    """
    A pure fraction with a numerator and denominator
    """
    __slots__ = "numerator", "denominator"
    numerator: float
    denominator: float


@dataclass
class _SuffixedNumber:
    """
    A suffixed number construct where the number is either a int, float, or fractional representation
    the suffix maps to a multiplier table (i/e 1 minute -> 60 seconds)
    """
    __slots__ = "number", "suffix"
    number: Union[float, _Fraction]
    suffix: str

    def value(self, multiplier_table: Dict[str, int]) -> Optional[int]:

        multiplier = multiplier_table.get(self.suffix)

        if multiplier is None:
            return None

        if isinstance(self.number, (float, int)):
            try:
                return int(multiplier * self.number)
            except ValueError:
                return None

        else:
            try:
                return int((multiplier * self.number.numerator) // self.number.denominator)
            except (ValueError, ZeroDivisionError):
                return None


@dataclass
class _TypedStr:
    """
    A typed string in the preprocessing stage, has not yet been processed as a suffixed number
    but has been typed as a number or suffix
    """
    __slots__ = "val", "typ"
    val: str
    typ: Literal["digit", "suffix"]


class _idx_ptr:
    """
    Helper method to wrap increments of indexes
    """
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


def _float_or_int(s: str) -> float:
    """
    Raises ValueError on failure
    """
    if "." in s:
        f = float(s)
        if f.is_integer():
            return int(f)
        else:
            return f
    else:
        return int(s)


def _num_from_typedstr(v: _TypedStr) -> Optional[Union[float, _Fraction]]:
    """
    Returns a number from a digit typed string
    """
    if v.typ == "digit":
        try:
            if "/" in v.val:
                if v.val.count("/") != 1:
                    return None

                num, denom = v.val.split("/")

                return _Fraction(_float_or_int(num), _float_or_int(denom))

            else:
                return _float_or_int(v.val)
        except ValueError:
            return None
    else:
        return None


def _str_to_tree(s: str) -> Optional[List[_SuffixedNumber]]:
    """
    Converts a string into a list of suffixed numbers
    """

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
        if tree[0].typ == "digit" and (n := _num_from_typedstr(tree[0])) is not None:
            # disallow fractions as non prefixed numbers
            if not isinstance(n, _Fraction):
                return [_SuffixedNumber(n, "s")]
            return None
        else:
            return None

    # assert len(tree) > 1

    # Can't start on a suffix
    if tree[0].typ == "suffix":
        return None

    if tree[-1].typ == "digit":
        return None

    # Assert that lengths are correct, should be asserted by previous logic
    if not len(tree) % 2 == 0:
        return None

    out: List[_SuffixedNumber] = []

    # alternating digit and suffix starting with digit and ending on suffix
    for i in range(0, len(tree), 2):

        digit = _num_from_typedstr(tree[i])

        if digit is None:
            return None

        if tree[i + 1].val not in _suffix_table:
            return None

        out.append(_SuffixedNumber(digit, tree[i + 1].val))

    return out


@dataclass
class Clock:
    """
    A dataclass representing a wall clock reading of hours minutes seconds and nanoseconds in military time
    mostly equivalent to a 'time' or 'clock' from libraries representing time as a date+time
    """
    hours: int
    minutes: int
    seconds: int
    nanoseconds: int


@dataclass
class Date:
    """
    A dataclass representing a date in terms of years, months, and days
    mostly equivalent to a 'date' from libraries representing time as a date+time
    """
    years: int
    months: int
    days: int


class Duration(int):
    def nanos(self) -> int:
        """
        Returns duration as nanoseconds
        """
        return self

    def micros(self) -> int:
        """
        Returns duration as microseconds
        """
        return self // _NANOS_PER_MICRO

    def millis(self) -> int:
        """
        Returns duration as milliseconds
        """
        return self // _NANOS_PER_MILLI

    def seconds(self) -> int:
        """
        Returns duration as seconds
        """
        return self // _NANOS_PER_SECOND

    def clock(self) -> Clock:
        """
        Returns duration as a Clock representation
        """

        nanos = self.nanos()

        seconds = nanos // _NANOS_PER_SECOND
        nanos %= _NANOS_PER_SECOND

        minutes = seconds // 60
        seconds %= 60

        hours = minutes // 60
        minutes %= 60

        return Clock(hours, minutes, seconds, nanos)

    @classmethod
    def from_clock(cls, clock: Clock) -> "Duration":
        """
        Constructs a Duration from a Clock object
        """
        return cls.from_hms(clock.hours, clock.minutes, clock.seconds, clock.nanoseconds)

    @classmethod
    def from_hms(cls, hours: int, minutes: int, seconds: int, nanos: Optional[int] = None) -> "Duration":
        """
        Constructs a Duration from hours minutes and seconds, and optionally nanoseconds
        Lower types will overflow into larger constructs (i/e 120 seconds will add up to 2 minutes added to the total duration)
        """

        if nanos is None:
            nanos = 0

        minutes += hours * 60
        seconds += minutes * 60
        nanos += seconds * _NANOS_PER_SECOND

        return cls(nanos)

    @classmethod
    def from_seconds(cls, seconds: int) -> "Duration":
        return cls(seconds * _NANOS_PER_SECOND)

    @classmethod
    def parse(cls, s: str) -> Optional["Duration"]:
        """
        Parses a Duration up to seconds accuracy
        Where number is a float or float/float fraction:
            Allows ({number}{suffix})+ where suffix is weeks|days|hours|minutes|seconds or singular or single char shorthands
            Parses {number} => seconds
            Parses {singular|single char} suffix => 1 of suffix type (day => 1day)

        Numbers are kept as integer values when possible, floating point values are subject to IEEE-754 64 bit limitations.
        Fraction numerators are multiplied by their suffix multiplier before being divided by their denominator, with floating point math starting where the first float is present

        :returns: Optional[Duration] - Return value, None if it could not be parsed
        """

        # Check if in supertable
        try:
            return cls.from_seconds(_super_table[s])
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
                v: Optional[int]
                if (v := i.value(_suffix_table)) is not None:
                    out += v
                else:
                    return None
            except ValueError:
                return None

        return cls.from_seconds(out)


class Time:
    """
    This libraries basic representation of a point in Time, contains methods to parse and manipulate itself
    """
    __slots__ = "_unix", "_monotonic", "_tz", "__dt_ptr"

    def __init__(self, *, unix: Optional[int] = None, tz: Optional[datetime.tzinfo] = None) -> None:
        """
        Default constructor, generates a Time from unix seconds and a timezone
        """

        # None tz == UTC
        self._tz: Optional[datetime.tzinfo] = tz

        # unix is in nanoseconds
        self._unix: int
        # monotonic is in nanoseconds and optionally set
        self._monotonic: Optional[int]

        if unix is None:
            self._unix = time.time_ns()
            self._monotonic = time.monotonic_ns()
        else:
            self._unix = unix * _NANOS_PER_SECOND
            self._monotonic = None

        # _unix and _tz must be frozen after __dt_ptr is set to preserve datetime accuracy, so disallow _unix and _tz editing
        self.__dt_ptr: Optional[datetime.datetime] = None

    def __format__(self, format_str: str) -> str:
        """
        Formats time using datetime strftime syntax
        """
        return self.as_datetime().strftime(format_str)

    def __eq__(self, other: object) -> bool:
        """
        Returns whether 2 time instants have the same time and timezone
        """
        if isinstance(other, Time):
            return self._unix == other._unix and self._tz == other._tz
        else:
            return False

    def __ne__(self, other: object) -> bool:
        return not self == other

    def __le__(self, other: "Time") -> bool:
        return self._unix <= other._unix

    def __lt__(self, other: "Time") -> bool:
        return self._unix < other._unix

    def __ge__(self, other: "Time") -> bool:
        return self._unix >= other._unix

    def __gt__(self, other: "Time") -> bool:
        return self._unix > other._unix

    def __sub__(self, other: "Time") -> Duration:
        return self.difference(other)

    def __add__(self, other: Duration) -> "Time":
        """
        Adds a Duration to a Time.
        
        Note that this does not account for irregularities with what we perceive as days/months
        (ex leap seconds, months have different amount of days)
        for those purposes, use add_(days|months|years)
        """

        new_unix = self._unix + other.nanos()
        return self.from_nanos(new_unix, tz=self._tz)

    def add_days(self, days: int) -> "Time":
        """
        Adds days to the time and returns a new Time object with the new time
        """

        dt_ptr = self.as_datetime()
        return self.from_datetime(dt_ptr + datetime.timedelta(days=days))

    def add_months(self, months: int) -> "Time":
        """
        Adds months to the time and returns a new Time object with the new time
        """

        dt_ptr = self.as_datetime()

        extra_years, new_months = divmod(months + dt_ptr.month, 12)
        # account for divmod returning range(0..12) instead of inclusive range(1..=12)
        new_months += 1

        return self.from_datetime(dt_ptr.replace(month=new_months, year=dt_ptr.year + extra_years))

    def add_years(self, years: int) -> "Time":
        """
        Adds years to the time and returns a new Time object with the new time
        """
        dt_ptr = self.as_datetime()

        return self.from_datetime(dt_ptr.replace(year=dt_ptr.year + years))

    @classmethod
    def now(cls) -> "Time":
        """
        Returns a UTC timezone current time object
        """
        return cls()

    @classmethod
    def from_nanos(cls, nanos: int, *, tz: Optional[datetime.tzinfo] = None) -> "Time":
        """
        Returns a new Time object from unix nanoseconds
        """
        # disable monotonic
        t = cls(unix=0, tz=tz)
        t._unix = nanos
        return t

    def has_monotonic(self) -> bool:
        """
        Reports whether this Time object contains a monotonic clock reading
        """
        return self._monotonic is not None

    def difference(self, other: "Time") -> Duration:
        """
        Calculates the difference between self and other and returns a Duration representing self-other
        Defaults to monotonic clock, fallsback to unix if either does not contain monotonic
        """

        if self._monotonic is not None and other._monotonic is not None:
            return Duration(self._monotonic - other._monotonic)
        else:
            return Duration(self._unix - other._unix)

    def elapsed(self) -> Duration:
        """
        Calculates the difference between current time and this Time object,
        Uses monotonic clock if object has monotonic, else fallsback to unix comparison
        """
        return self.now().difference(self)

    def clock(self) -> Clock:
        """
        Returns a wall clock reading of hours, minutes, and seconds in the current timezone
        """
        dt = self.as_datetime()
        nanos = self._unix % _NANOS_PER_SECOND
        return Clock(dt.hour, dt.minute, dt.second, nanos)

    def date(self) -> Date:
        """
        Returns a date reading of years, months, and days in the current timezone
        """
        dt = self.as_datetime()
        return Date(dt.year, dt.month, dt.day)

    def UTC(self) -> "Time":
        """
        Returns a new time object with the timezone set to UTC, preserving monotonic
        """
        new = self.from_nanos(self._unix)
        # Preserve monotonic as timezone is not related
        new._monotonic = self._monotonic
        return new

    def unix(self) -> int:
        """
        Returns Unix seconds
        """
        return self._unix // _NANOS_PER_SECOND

    def unix_milli(self) -> int:
        """
        Returns Unix milliseconds
        """
        return self._unix // _NANOS_PER_MILLI

    def unix_micro(self) -> int:
        """
        Returns Unix microseconds
        """
        return self._unix // _NANOS_PER_MICRO

    def unix_nano(self) -> int:
        """
        Returns Unix nanoseconds
        """
        return self._unix

    def as_datetime(self) -> datetime.datetime:
        """
        Returns an aware datetime of the current time
        """
        if self.__dt_ptr is None:
            dt = datetime.datetime.fromtimestamp(self.unix()).astimezone(datetime.timezone.utc)
            self.__dt_ptr = dt.astimezone(self._tz if self._tz is not None else datetime.timezone.utc)

        # shallow copy ensures __dt_ptr remains immutable
        return pycopy.copy(self.__dt_ptr)

    @classmethod
    def from_datetime(cls, dt: datetime.datetime, /) -> "Time":
        """
        Builds a Time object from a datetime object, assumes naive datetimes are Localtime
        Warning: Calling this method with a naive datetime object may not return the wanted Time instant
        """
        if dt.tzinfo is not None and dt.tzinfo != datetime.timezone.utc:
            tz = dt.tzinfo
        else:
            tz = None

        nanos = int(dt.timestamp() * _NANOS_PER_SECOND)
        nanos += dt.microsecond * _NANOS_PER_MICRO

        self = cls.from_nanos(nanos, tz=tz)

        # cheap clone datetime if it is aware instead of having to generate a new one later
        if dt.tzinfo is not None:
            self.__dt_ptr = pycopy.copy(dt)

        return self
