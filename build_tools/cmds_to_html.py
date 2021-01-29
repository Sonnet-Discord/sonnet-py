# Tools to autogenerate documentation from sonnet source code
# Ultrabear 2021

import importlib
import os
import sys

sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')

command_modules = []
command_modules_dict = {}
# Init imports
for f in os.listdir('./cmds'):
    if f.startswith("cmd_") and f.endswith(".py"):
        command_modules.append(importlib.import_module(f[:-3]))
    # Update hashmaps
    for module in command_modules:
        command_modules_dict.update(module.commands)

outlist = []
starter_padding = 3
outlist.append("")


# Make alias mappings
aliashmap = {}
[aliashmap.update(module.commands) for module in command_modules]
aliasmap = {}
for i in aliashmap.keys():
    if 'alias' in aliashmap[i].keys():
        if aliashmap[i]['alias'] in aliasmap.keys():
            aliasmap[aliashmap[i]['alias']].append(i)
        else:
            aliasmap[aliashmap[i]['alias']] = [i]

for module in sorted(command_modules, key=lambda a: a.category_info['name']):

    # Append header
    outlist.append(f"<h2 id=\"{module.category_info['name']}\">")
    outlist.append(f"\t<a href=\"#{module.category_info['name']}\">{module.category_info['pretty_name']}</a>")
    outlist.append("</h2>")

    # Create table
    outlist.append("<table>")

    outlist.append("\t<tr>")
    outlist.append("\t\t<th>Command Syntax</th>")
    outlist.append("\t\t<th>Description</th>")
    outlist.append("\t\t<th>Aliases</th>")
    outlist.append("\t\t<th>Permission Level</th>")
    outlist.append("\t</tr>")

    for i in [i for i in module.commands if 'alias' not in module.commands[i].keys()]:

        command_name = module.commands[i]["pretty_name"].replace("<", "&lt;").replace(">", "&gt;").split(" ")
        command_name = f"{command_name[0]} " + "&nbsp;".join(command_name[1:]).replace("&gt;&nbsp;&lt;", "&gt; &lt;")

        command_perms = module.commands[i]['permission'][0].upper()
        command_perms += module.commands[i]['permission'][1:].lower()

        if i in aliasmap.keys():
            aliases = ", ".join(aliasmap[i])
        else:
            aliases = ""

        outlist.append("\t<tr>")
        outlist.append(f"\t\t<td>{command_name}</td>")
        outlist.append(f"\t\t<td>{module.commands[i]['description']}</td>")
        outlist.append(f"\t\t<td>{aliases}</td>")
        outlist.append(f"\t\t<td>{command_perms}</td>")
        outlist.append("\t</tr>")

    outlist.append("</table>")

print(("\n" + "\t" * starter_padding).join(outlist))
