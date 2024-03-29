# Simple program to help add words to the wordlist

from typing import Set

with open("common/wordlist.txt", encoding="utf-8") as fp:
    used: Set[str] = {i for i in fp.read().split("\n") if i}

try:

    while True:
        data = input("> ")
        if data in used:
            print("Already taken")
        elif data and all('a' <= i <= 'z' for i in data):
            used.add(data)
        else:
            print("Nil input/contains non a-z")

except (KeyboardInterrupt, EOFError):
    print("Exiting")

finally:
    with open("common/wordlist.txt", "w", encoding="utf-8") as fp:
        for i in sorted(used):
            fp.write(i)
            fp.write("\n")
    print("Saved to disk")
