# Testing lib to ensure no invalid unicode is inside of code files, obfuscating malware
# Ultrabear 2022

import string
import glob
import sys

from typing import Final, List

# star emoji because of sonnet_cfg.py
# kusa rune because of funny joke
VALID_FCHARS: Final = set(string.printable + "\u2b50" + "\u8349")


def assertfile(f: str, ferrors: List[str]) -> None:
    with open(f, "r") as fp:
        for line, linev in enumerate(fp):
            for col, v in enumerate(linev):
                if not v in VALID_FCHARS:
                    ferrors.append(f"{f}:{line+1}:{col+1}: Unicode rune {hex(ord(v))} is not in allowed pool")


def main() -> int:

    ferrors: List[str] = []

    for f in glob.iglob("**/*.py", recursive=True):
        assertfile(f, ferrors)

    if ferrors:
        print("\n".join(ferrors))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
