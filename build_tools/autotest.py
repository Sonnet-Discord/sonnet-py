import threading
import tempfile
import os
import sys
import io

from typing import Dict, Any

tests = {
    "pyflakes": "pyflakes .",
    "mypy": "mypy *.py */*.py --ignore-missing-imports --strict --implicit-reexport --warn-unreachable",
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
    e = io.StringIO()
    e.write(testout[i]["stdout"].read().decode("utf8"))
    e.write(testout[i]["stderr"].read().decode("utf8"))

    print(f"\033[94m{testout[i]['args']}\033[0m")
    if v := e.getvalue(): print(v, end="")
