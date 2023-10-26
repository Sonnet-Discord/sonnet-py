# Design Patterns
This is a semi formal documentation of common design patterns in Sonnet, it stands opposed to `BANNED.md` which is a list of things to not do; `DESIGN.md` is a list of things that should be done
## Typing
All Sonnet code should be fully typed as it is written, and pass testing through `mypy` and `pyright` typecheckers for comprehensive coverage, use of `Any`/`cast`/`# type: ignore` is discouraged
## Command Naming
Commands should follow a common convention of naming:
### Commands that...
- Set a configuration: `set-{name}`
- Set a logging channel: `{name}-log`
- Do a discord api action (ex: ban): `{action}`
- Are part of a module: `{module}-{name}`
### Character set
- Commands should not have whitespace in their name, dashes (`-`) should be used where multiple words should be stringed together (ex: `list-aliases`)  
