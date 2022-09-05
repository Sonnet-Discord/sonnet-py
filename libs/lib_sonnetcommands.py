# Command backwards compatible api wrapper that allows new endpoints
# Ultrabear 2021

import inspect
import asyncio
from dataclasses import dataclass
from typing import (Any, Callable, Coroutine, Dict, List, Protocol, Tuple, Union, cast, Optional, Set)
from typing_extensions import TypeGuard  # pytype: disable=not-supported-yet

import discord
import lib_lexdpyk_h as lexdpyk


class ExecutableT(Protocol):
    def __call__(self, message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Coroutine[Any, Any, Any]:
        ...


class ExecutableCtxT(Protocol):
    def __call__(self, message: discord.Message, args: List[str], client: discord.Client, ctx: "CommandCtx") -> Coroutine[Any, Any, Any]:
        ...


PermissionT = Union[str, Tuple[str, Callable[[discord.Message], bool]]]

_allowpool = {
    "cache": "keep",
    "permission": "everyone",
    }


class _ContextButton(discord.ui.Button[Any]):
    __slots__ = "private_message", "user_id", "called_out_ids"

    def __init__(self, label: str, private_message: str, user_id: int) -> None:
        super().__init__(style=discord.ButtonStyle.danger, label=label)
        self.private_message = private_message
        self.user_id = user_id
        self.called_out_ids: Set[int] = set()

    async def callback(self, interaction: discord.Interaction) -> None:

        if interaction.user.id == self.user_id:

            send = asyncio.create_task(interaction.response.send_message(self.private_message, ephemeral=True))
            if interaction.message is not None:
                await interaction.message.edit(view=None)

            # make events happen at same time
            await send

        else:
            if interaction.user.id not in self.called_out_ids:
                await interaction.response.send_message("Only the sender of the command may read error details.", ephemeral=True)
                self.called_out_ids.add(interaction.user.id)


class CommandError(Exception):
    """
    CommandError is an error that can be raised by a command

    It is treated specially by the exception handler such that it
    will print the error string to the current channel instead of raising to the kernel, and have the same effect as return != 1
    it should be used for cleaner user error handling

    `await message.channel.send("error"); return 1`
    may be replaced with
    `raise CommandError("error")`
    for the same effect

    Additionally a private_message may be passed to CommandError,
    allowing extra info to be attached that is only sent to the specific user
    this allows echoing user input as it is self contained
    """
    __slots__ = "private_message",

    def __init__(self, *args: object, private_message: Optional[str] = None) -> None:

        super().__init__(*args)
        self.private_message = private_message

    async def send(self, message: discord.Message) -> None:
        """
        Sends the CommandError to the provided message channel and author
        
        ignores permission errors on message sending
        """

        try:
            if self.private_message is None:
                await message.channel.send(str(self))
            else:
                view = discord.ui.View(timeout=60)

                view.add_item(_ContextButton("Details", self.private_message, message.author.id))

                msg = await message.channel.send(str(self), view=view)
                await view.wait()
                await msg.edit(view=None)
        except discord.errors.Forbidden:
            pass


@dataclass
class CommandCtx:
    """
    A Context dataclass for a command, contains useful data to pull from for various running commands.
    This class is not meant to be init by commands, doing so is undefined behaviour.
    """
    __slots__ = "stats", "cmds", "ramfs", "kernel_ramfs", "bot_start", "dlibs", "main_version", "conf_cache", "verbose", "cmds_dict", "automod"
    # Stats about the time it took to do various tasks in message handling, only kept around for ping command
    stats: Dict[str, int]
    # List of command modules passed by kernel
    cmds: List[lexdpyk.cmd_module]
    # Temp ramfs passed by kernel
    ramfs: lexdpyk.ram_filesystem
    # Permanent ramfs passed by kernel
    kernel_ramfs: lexdpyk.ram_filesystem
    # Time in unix seconds that the bot started at
    bot_start: float
    # List of dlib modules passed by kernel
    dlibs: List[lexdpyk.dlib_module]
    # Version info of the kernel
    main_version: str
    # An instance of the default guild cache, contains automod data
    conf_cache: Dict[str, Any]
    # Whether this command should be verbose in its output, also serves to signal when a command is a subcommand
    verbose: bool
    # Global dict of commands passed by kernel
    cmds_dict: lexdpyk.cmd_modules_dict
    # Whether the command was triggered by automod
    automod: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats": self.stats,
            "cmds": self.cmds,
            "ramfs": self.ramfs,
            "kernel_ramfs": self.kernel_ramfs,
            "bot_start": self.bot_start,
            "dlibs": self.dlibs,
            "main_version": self.main_version,
            "conf_cache": self.conf_cache,
            "verbose": self.verbose,
            "cmds_dict": self.cmds_dict,
            "automod": self.automod,
            }


def cache_sweep(cdata: Union[str, "SonnetCommand"], ramfs: lexdpyk.ram_filesystem, guild: discord.Guild) -> None:
    """
    Runs a cache sweep with a given cache behavior or direct SonnetCommand
    Useful for processing arbitrary commands and asserting proper cache handling
    """

    if isinstance(cdata, str):
        cache = cdata
    else:
        cache = cdata.cache

    if cache in ["purge", "regenerate"]:
        for i in ["caches", "regex"]:
            try:
                ramfs.rmdir(f"{guild.id}/{i}")
            except FileNotFoundError:
                pass

    elif cache.startswith("direct:"):
        for i in cache[len('direct:'):].split(";"):
            try:
                if i.startswith("(d)"):
                    ramfs.rmdir(f"{guild.id}/{i[3:]}")
                elif i.startswith("(f)"):
                    ramfs.remove_f(f"{guild.id}/{i[3:]}")
                else:
                    raise RuntimeError("Cache directive is invalid")
            except FileNotFoundError:
                pass


def _iskwargcallable(func: Union[ExecutableT, ExecutableCtxT]) -> TypeGuard[ExecutableT]:
    spec = inspect.getfullargspec(func)
    return len(spec.args) == 3 and spec.varkw is not None


def _isctxcallable(func: Union[ExecutableT, ExecutableCtxT]) -> TypeGuard[ExecutableCtxT]:
    spec = inspect.getfullargspec(func)
    return len(spec.args) == 4


def CallKwargs(func: Union[ExecutableT, ExecutableCtxT]) -> ExecutableT:
    if _iskwargcallable(func):
        return func
    elif _isctxcallable(func):
        # Closures go brr
        def KwargsToCtx(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Coroutine[None, None, Any]:
            ctx = CommandCtx(**kwargs)
            # we need to cast here because mypy??
            return cast(ExecutableCtxT, func)(message, args, client, ctx)

        return KwargsToCtx

    else:
        raise TypeError(f"Func {func} parameters are neither a ctx callable or kwargs callable")


def CallCtx(func: Union[ExecutableCtxT, ExecutableT]) -> ExecutableCtxT:
    if _isctxcallable(func):

        return func

    elif _iskwargcallable(func):

        def CtxToKwargs(message: discord.Message, args: List[str], client: discord.Client, ctx: CommandCtx) -> Coroutine[None, None, Any]:
            kwargs = ctx.to_dict()
            return func(message, args, client, **kwargs)

        return CtxToKwargs

    else:
        raise TypeError(f"Func {func} parameters are neither a ctx callable or kwargs callable")


# type ignore needed because mypy expects something only possible in 3.9+
class SonnetCommand(dict):  # type: ignore[type-arg]
    __slots__ = ()

    def __init__(self, vals: Dict[str, Any], aliasmap: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
        """
        Init a new sonnetcommand instance.
        If an aliasmap is passed, the command will be checked for if it has an alias and inherit it into itself if it does
        """
        if aliasmap is not None and 'alias' in vals:
            vals = aliasmap[vals['alias']]
        super().__init__(vals)

    def __getitem__(self, item: Any) -> Any:
        # override execute to return a CallKwargs to maintain backwards compat
        if item == "execute":
            return CallKwargs(super().__getitem__(item))
        try:
            return super().__getitem__(item)
        except KeyError:
            return _allowpool[item]

    def get(self, item: Any, default: Any = None) -> Any:
        try:
            return self[item]
        except KeyError:
            return default

    def __contains__(self, item: Any) -> bool:
        if item in _allowpool:
            return True
        else:
            return super().__contains__(item)

    def sweep_cache(self, ramfs: lexdpyk.ram_filesystem, guild: discord.Guild) -> None:
        """
        Helper method to call cache_sweep on the current SonnetCommand
        """
        cache_sweep(self, ramfs, guild)

    @property
    def execute(self) -> ExecutableT:
        return cast(ExecutableT, self["execute"])

    @property
    def execute_kwargs(self) -> ExecutableT:
        return CallKwargs(super().__getitem__("execute"))

    @property
    def execute_ctx(self) -> ExecutableCtxT:
        return CallCtx(super().__getitem__("execute"))

    @property
    def cache(self) -> str:
        return str(self["cache"])

    @property
    def permission(self) -> PermissionT:
        return cast(PermissionT, self["permission"])

    @property
    def description(self) -> str:
        return str(self["description"])

    @property
    def pretty_name(self) -> str:
        return str(self["pretty_name"])

    @property
    def rich_description(self) -> str:
        return str(self["rich_description"])
