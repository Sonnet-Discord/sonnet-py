import threading
import tempfile
import os
import sys

from typing import Dict, Any

tests = {
    "pyflakes": "pyflakes .",
    "mypy": "mypy *.py */*.py --ignore-missing-imports",
    "pylint": "pylint */ -E",
    "yapf": "yapf -d -r .",
    }

notttest = set(sys.argv[1:])

for i in list(tests.keys()):
    if i in notttest:
        del tests[i]

testout: Dict[str, Any] = {}
for i in tests:
    testout[i] = {
        "stdout": tempfile.NamedTemporaryFile(),
        "stderr": tempfile.NamedTemporaryFile(),
        "args": tests[i],
        }

    t = threading.Thread(target=os.system, args=(testout[i]["args"] + f" > {testout[i]['stdout'].name} 2> {testout[i]['stderr'].name}", ))
    t.start()
    testout[i]["p"] = t

for i in testout:
    testout[i]['p'].join()
    e: str = ""
    e += testout[i]["stdout"].read().decode("utf8")
    e += testout[i]["stderr"].read().decode("utf8")

    print(f"\033[94m{testout[i]['args']}\033[0m")
    if e: print(e, end="")
