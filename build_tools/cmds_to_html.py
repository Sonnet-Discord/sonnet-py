# Tools to autogenerate documentation from sonnet source code
# Ultrabear 2021

import importlib
import os
import sys
from typing import Dict, List, cast

sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')

import lib_lexdpyk_h as lexdpyx

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

    cache = command_modules_dict[command]["cache"]
    if cache in ["purge", "regenerate", "keep"]:
        continue

    elif cache.startswith("direct:"):
        for i in cache[len('direct:'):].split(";"):
            if i.startswith("(d)") or i.startswith("(f)"):
                pass
            else:
                raise SyntaxError(f"ERROR IN {command} CACHE BEHAVIOR ({cache})")
        continue

    raise SyntaxError(f"ERROR IN {command} CACHE BEHAVIOR ({cache})")

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

    for i in [i for i in module.commands if 'alias' not in module.commands[i].keys()]:

        command_name = module.commands[i]["pretty_name"]

        command_perms = module.commands[i]['permission'][0].upper()
        command_perms += module.commands[i]['permission'][1:].lower()

        if i in aliasmap.keys():
            aliases = ", ".join(aliasmap[i])
        else:
            aliases = "None"

        outlist.append("\t<tr>")
        outlist.append(f"\t\t<td>{escape(command_name)}</td>")
        outlist.append(f"\t\t<td>{escape(module.commands[i]['description'])}</td>")
        outlist.append(f"\t\t<td>{escape(aliases)}</td>")
        outlist.append(f"\t\t<td>{escape(command_perms)}</td>")
        outlist.append("\t</tr>")

    outlist.append("</table>")

print(("\n" + "\t" * starter_padding).join(outlist))
