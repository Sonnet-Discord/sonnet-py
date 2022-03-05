# Tools to autogenerate documentation from sonnet source code
# Ultrabear 2021
if __name__ != "__main__": raise ImportError("This file is a script, do not import it.")

import importlib
import os
import sys
import inspect

from typing import Dict, List, cast

sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')

import lib_lexdpyk_h as lexdpyx
from lib_sonnetcommands import SonnetCommand

command_modules: List[lexdpyx.cmd_module] = []
command_modules_dict: lexdpyx.cmd_modules_dict = {}
# Init imports
for f in os.listdir('./cmds'):
    if f.startswith("cmd_") and f.endswith(".py"):
        command_modules.append(cast(lexdpyx.cmd_module, importlib.import_module(f[:-3])))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)

outlist: List[str] = []
starter_padding: int = 0
outlist.append("")

# Test for valid cache formatting
for command in command_modules_dict:
    if "alias" in command_modules_dict[command]:
        continue

    sonnetcmd = SonnetCommand(command_modules_dict[command])

    cache = sonnetcmd.cache
    if cache in ["purge", "regenerate", "keep"]:
        continue

    elif cache.startswith("direct:"):
        for i in cache[len('direct:'):].split(";"):
            if not (i.startswith("(d)") or i.startswith("(f)")):
                raise SyntaxError(f"ERROR IN {command} CACHE BEHAVIOR ({cache})")
        continue

    # sonnetcmd.execute might point to lib_sonnetcommands if it builds a closure for backwards compat, so get the raw value
    execmodule: str = command_modules_dict[command]['execute'].__module__

    raise SyntaxError(f"ERROR IN [{execmodule} : {command}] CACHE BEHAVIOR ({cache})")

# Test for valid permission definition
for command in command_modules_dict:
    if "alias" in command_modules_dict[command]:
        continue

    cmd = SonnetCommand(command_modules_dict[command])
    # cmd.execute might point to lib_sonnetcommands if it builds a closure for backwards compat, so get the raw value
    execmodule = command_modules_dict[command]['execute'].__module__

    if isinstance(cmd.permission, str):
        if cmd.permission in ["everyone", "moderator", "administrator", "owner"]:
            continue
    elif isinstance(cmd.permission, (tuple, list)):
        if isinstance(cmd.permission[0], str) and callable(cmd.permission[1]):
            spec = inspect.getfullargspec(cmd.permission[1])
            if len(spec.args) > 2:  # Support for object instances with self first argument
                raise SyntaxError(f"ERROR IN [{execmodule} : {command}] PERMISSION FUNCTION({cmd.permission[1]}) IS NOT VALID (EXPECTED ONE ARGUMENT)")
            continue

    raise SyntaxError(f"ERROR IN [{execmodule} : {command}] PERMISSION TYPE({cmd.permission}) IS NOT VALID")

# Test for aliases pointing to existing commands
for command in command_modules_dict:
    if "alias" not in command_modules_dict[command]:
        continue

    if command_modules_dict[command]['alias'] in command_modules_dict:
        continue

    raise SyntaxError(f"ERROR IN ALIAS:{command}, NO SUCH COMMAND {command_modules_dict[command]['alias']}")

# Make alias mappings
aliasmap: Dict[str, List[str]] = {}
for i in command_modules_dict:
    if 'alias' in command_modules_dict[i]:
        if command_modules_dict[i]['alias'] in aliasmap:
            aliasmap[command_modules_dict[i]['alias']].append(i)
        else:
            aliasmap[command_modules_dict[i]['alias']] = [i]


# Slow, do i care? no
def escape(s: str) -> str:
    repl: Dict[str, str] = {
        "&": "&amp;",
        "'": "&#39;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&#34;",
        }

    for i in repl:
        s = s.replace(i, repl[i])

    return s


def titlecase(s: str) -> str:
    return s[0].upper() + s[1:].lower()


for module in sorted(command_modules, key=lambda a: a.category_info['name']):

    # Assert all these fields exist
    assert isinstance(module.version_info, str), f"{module.__name__}.version_info malformed"
    assert isinstance(module.category_info, dict), f"{module.__name__}.category_info malformed"
    assert isinstance(module.commands, dict), f"{module.__name__}.commands malformed"

    # Append header
    outlist.append(f"<h2 id=\"{escape(module.category_info['name'])}\">")
    outlist.append(f"\t<a href=\"#{escape(module.category_info['name'])}\">{escape(module.category_info['pretty_name'])}</a>")
    outlist.append("</h2>")

    # Create table
    outlist.append("<table class=\"lastctr\">")

    outlist.append("\t<tr>")
    outlist.append("\t\t<th>Command Syntax</th>")
    outlist.append("\t\t<th>Description</th>")
    outlist.append("\t\t<th>Aliases</th>")
    outlist.append("\t\t<th>Permission Level</th>")
    outlist.append("\t</tr>")

    for i in filter(lambda i: "alias" not in module.commands[i], module.commands):
        sonnetcmd = SonnetCommand(module.commands[i])

        command_name = sonnetcmd.pretty_name
        description = sonnetcmd.description

        aliases = ", ".join(aliasmap[i]) if i in aliasmap else "None"

        if isinstance(sonnetcmd.permission, str):
            command_perms = titlecase(sonnetcmd.permission)
        else:
            command_perms = titlecase(sonnetcmd.permission[0])

        outlist.append("\t<tr>")
        outlist.append(f"\t\t<td>{escape(command_name)}</td>")
        outlist.append(f"\t\t<td>{escape(description)}</td>")
        outlist.append(f"\t\t<td>{escape(aliases)}</td>")
        outlist.append(f"\t\t<td>{escape(command_perms)}</td>")
        outlist.append("\t</tr>")

    outlist.append("</table>")

print(("\n" + "\t" * starter_padding).join(outlist))
