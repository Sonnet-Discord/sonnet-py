# Intro
print("Booting LeXdPyK test env")

# Import core systems
import os, importlib, sys

# Initialize kernel workspace
sys.path.insert(1, os.getcwd() + '/cmds')
sys.path.insert(1, os.getcwd() + '/common')
sys.path.insert(1, os.getcwd() + '/libs')
sys.path.insert(1, os.getcwd() + '/dlibs')

# Define debug commands

from typing import List, Any, cast
import lib_lexdpyk_h as lexdpyk

command_modules: List[lexdpyk.cmd_module] = []
command_modules_dict: lexdpyk.cmd_modules_dict = {}
dynamiclib_modules: List[lexdpyk.dlib_module] = []
dynamiclib_modules_dict: lexdpyk.dlib_modules_dict = {}


# Define kernel syntax error
class KernelSyntaxError(SyntaxError):
    pass


def kernel_load_command_modules(*args: str) -> Any:
    print("Loading Kernel Modules")
    # Globalize variables
    global command_modules, command_modules_dict, dynamiclib_modules, dynamiclib_modules_dict
    command_modules = []
    command_modules_dict = {}
    dynamiclib_modules = []
    dynamiclib_modules_dict = {}
    importlib.invalidate_caches()

    # Init return state
    err = []

    # Init imports
    for f in filter(lambda f: f.startswith("cmd_") and f.endswith(".py"), os.listdir('./cmds')):
        print(f)
        try:
            command_modules.append(cast(lexdpyk.cmd_module, importlib.import_module(f[:-3])))
        except Exception as e:
            err.append([e, f[:-3]])
    for f in filter(lambda f: f.startswith("dlib_") and f.endswith(".py"), os.listdir("./dlibs")):
        print(f)
        try:
            dynamiclib_modules.append(cast(lexdpyk.dlib_module, importlib.import_module(f[:-3])))
        except Exception as e:
            err.append([e, f[:-3]])

    # Update hashmaps
    for cmodule in command_modules:
        try:
            command_modules_dict.update(cmodule.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), cmodule.__name__])
    for dmodule in dynamiclib_modules:
        try:
            dynamiclib_modules_dict.update(dmodule.commands)
        except AttributeError:
            err.append([KernelSyntaxError("Missing commands"), dmodule.__name__])

    if err: return ("\n".join([f"Error importing {i[1]}: {type(i[0]).__name__}: {i[0]}" for i in err]), [i[0] for i in err])


if e := kernel_load_command_modules():
    print(e[0])
    sys.exit(1)
