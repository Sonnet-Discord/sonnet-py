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

# Make alias mappings
aliasmap: Dict[str, List[str]] = {}
for i in command_modules_dict:
    if 'alias' in command_modules_dict[i]:
        if command_modules_dict[i]['alias'] in aliasmap:
            aliasmap[command_modules_dict[i]['alias']].append(i)
        else:
            aliasmap[command_modules_dict[i]['alias']] = [i]

for module in sorted(command_modules, key=lambda a: a.category_info['name']):

    # Append header
    outlist.append(f"<h2 id=\"{module.category_info['name']}\">")
    outlist.append(f"\t<a href=\"#{module.category_info['name']}\">{module.category_info['pretty_name']}</a>")
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

        command_name = module.commands[i]["pretty_name"].replace("<", "&lt;").replace(">", "&gt;")

        command_perms = module.commands[i]['permission'][0].upper()
        command_perms += module.commands[i]['permission'][1:].lower()

        if i in aliasmap.keys():
            aliases = ", ".join(aliasmap[i])
        else:
            aliases = "None"

        outlist.append("\t<tr>")
        outlist.append(f"\t\t<td>{command_name}</td>")
        outlist.append(f"\t\t<td>{module.commands[i]['description']}</td>")
        outlist.append(f"\t\t<td>{aliases}</td>")
        outlist.append(f"\t\t<td>{command_perms}</td>")
        outlist.append("\t</tr>")

    outlist.append("</table>")

print(("\n" + "\t" * starter_padding).join(outlist))
