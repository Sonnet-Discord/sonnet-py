# Banned list
This is a list of the dont's of Sonnet, some apply to Python in general.  
None of the things listed below should happen in Sonnet.
# Absolutely not
- Do not have blind excepts, this means a `try:` `except:` statement with no specific error to catch
- Do not have try excepts that cover more than one or a few lines
  - This can be ommited if the errors caught are custom errors or errors that will only be on absolutely known lines
- Do not use `input()` or `print()` unless it is for debug or exceptions
  - Do not use `input()` even for debugging, it blocks asyncio
- Respect asyncio, do not use threading or multiprocessing, they are not designed to work together and introduce bugs
- Do not install libraries to do basic things, unless the libraries are stdlib
- Do not use `sys.setrecursionlimit()` to further utilize the ramfs, it will segfault
- Do not trust user input
- Do not trust the filesystem will not be corrupt
- Do not trust the database will not be corrupt
- `turing:`
- Do not hand end users turing complete
- **Do not hand end users turing complete**
- `goto turing;`
- Do not hand bot owners turing complete, but let them break things a little
- Do not do something for an end user, they must ask for it
- Do not feel bad if you break windows compat, no one should use windows anyways
- Do not install sonnet on windows, it will hopefully break
- Do not use `string1 + string2` operations often, they are slow and eat ram 
  - (tl;dr it has to allocate a new string that is the length of both strings combined, eating ram and being slow with lots of small mallocs)
  - Use StringIO() or str.join() instead, with fstrings for readability
	  - Combine all 3 `buf.write("\n".join([f"item {i} is {v}" for i, v in enumerate(data)]))`
# Basic Heresy
- Do not use eval:
```py
__import__("sys").setrecursionlimit(2**30)or(not(a:=(lambda: a())))or a()
```
- Do not use exec:
```py
v = __import__("sys").setrecursionlimit(2**30)or(not(a:=(lambda: a())))or a()
```
- Do not use third party library endpoints that have had a bug
- Do not use deprecated endpoints

