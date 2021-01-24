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
    outlist.append("\t\t<th>Permission Level</th>")
    outlist.append("\t</tr>")

    for i in module.commands:

        command_name = module.commands[i]["pretty_name"].replace("<", "&lt;").replace(">", "&gt;")

        command_perms = module.commands[i]['permission'][0].upper()
        command_perms += module.commands[i]['permission'][1:].lower()

        outlist.append("\t<tr>")
        outlist.append(f"\t\t<td>{command_name}</th>")
        outlist.append(f"\t\t<td>{module.commands[i]['description']}</th>")
        outlist.append(f"\t\t<td>{command_perms}</th>")
        outlist.append("\t</tr>")

    outlist.append("</table>")

print(("\n" + "\t" * starter_padding).join(outlist))
