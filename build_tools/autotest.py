import threading
import sys
import subprocess

from typing import Dict, Any, Union, List


# Wrapper around string to make the command run in sh instead of pexec
class Shell(str):
    ...


# Represents a ascii escaped color string
class Color:
    red = "\033[91m"
    blue = "\033[94m"
    reset = "\033[0m"


def run(args: Union[List[str], str], shell: bool, hm: Dict[str, Any]) -> None:
    ret = subprocess.run(args, shell=shell, capture_output=True)
    hm["stdout"] = ret.stdout
    hm["stderr"] = ret.stderr


def initjobs(tests: Dict[str, Union[str, Shell]]) -> Dict[str, Dict[str, Any]]:

    testout: Dict[str, Dict[str, Any]] = {}
    for k, v in tests.items():
        testout[k] = {
            "args": v,
            }

        flag = isinstance(v, Shell)
        args = v if flag else v.split()

        t = threading.Thread(target=run, args=(args, flag, testout[k]))
        testout[k]["p"] = t
        t.start()

    return testout


def finishjobs(testout: Dict[str, Dict[str, Any]]) -> None:

    for _, v in testout.items():
        v['p'].join()

        err = v["stdout"].decode("utf8") + v["stderr"].decode("utf8")

        cmdfmt = f"{Color.blue}{v['args']}{Color.reset}"
        isshell = f'{Color.red}sh -c ' * isinstance(v['args'], Shell)

        print(isshell + cmdfmt)
        if err: print(err, end="")


def main() -> None:

    tests: Dict[str, Union[str, Shell]] = {
        "pyflakes": "pyflakes .",
        "mypy": "mypy . --ignore-missing-imports --strict --warn-unreachable",
        "yapf": "yapf -drp .",
        "pylint": Shell("pylint */ -E -j4"),
        "pytype": "pytype .",
        }

    nottest = set(sys.argv[1:])

    for i in list(tests):
        if i in nottest:
            del tests[i]

    finishjobs(initjobs(tests))


if __name__ == "__main__":
    main()
