import threading
import sys
import subprocess

from dataclasses import dataclass

from typing import Dict, Optional, Union, List


# Wrapper around string to make the command run in sh instead of pexec
class Shell(str):
    __slots__ = ()


# Represents a ascii escaped color string
class Color:
    __slots__ = ()
    red = "\033[91m"
    blue = "\033[94m"
    reset = "\033[0m"


@dataclass
class RunningProc:
    args: str
    stdout: bytes
    stderr: bytes
    thread: Optional[threading.Thread]


def run(args: Union[List[str], str], shell: bool, hm: RunningProc) -> None:
    ret = subprocess.run(args, shell=shell, capture_output=True)
    hm.stdout = ret.stdout
    hm.stderr = ret.stderr


def initjobs(tests: Dict[str, Union[str, Shell]]) -> Dict[str, RunningProc]:

    testout: Dict[str, RunningProc] = {}

    for k, v in tests.items():
        testout[k] = RunningProc(v, b"", b"", None)

        flag = isinstance(v, Shell)
        args = v if flag else v.split()

        t = threading.Thread(target=run, args=(args, flag, testout[k]))
        testout[k].thread = t
        t.start()

    return testout


def finishjobs(testout: Dict[str, RunningProc]) -> None:

    for _, v in testout.items():
        assert v.thread is not None

        v.thread.join()

        err = v.stdout.decode("utf8") + v.stderr.decode("utf8")

        cmdfmt = f"{Color.blue}{v.args}{Color.reset}"
        isshell = f'{Color.red}sh -c ' * isinstance(v.args, Shell)

        print(isshell + cmdfmt)
        if err: print(err, end="")


def main() -> None:

    tests: Dict[str, Union[str, Shell]] = {
        "pyflakes": "pyflakes .",
        "mypy": "mypy . --ignore-missing-imports --strict --warn-unreachable --python-version 3.8",
        "yapf": "yapf -drp .",
        "pylint": Shell("pylint **/*.py -E -j4 --py-version=3.8"),
        #"pytype": "pytype .",
        }

    nottest = set(sys.argv[1:])

    for i in list(tests):
        if i in nottest:
            del tests[i]

    finishjobs(initjobs(tests))


if __name__ == "__main__":
    main()
