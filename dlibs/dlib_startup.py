# Handlers for initializing the bot and guilds
# Ultrabear 2021

import importlib

import discord, time, asyncio

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)
import lib_loaders

importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import inc_statistics_better, datetime_now

from typing import Dict, Callable, Any, List, Tuple


async def attempt_unmute(Client: discord.Client, mute_entry: Tuple[str, str, str, int]) -> None:

    with db_hlapi(int(mute_entry[0])) as db:
        db.unmute_user(infractionid=mute_entry[1])
        mute_role_id = db.grab_config("mute-role")

    if (guild := Client.get_guild(int(mute_entry[0]))) and mute_role_id:
        if (user := guild.get_member(int(mute_entry[2]))) and (mute_role := guild.get_role(int(mute_role_id))):
            try:
                await user.remove_roles(mute_role)
            except discord.errors.Forbidden:
                pass


async def on_ready(**kargs: Any) -> None:

    inc_statistics_better(0, "on-ready", kargs["kernel_ramfs"])

    Client: discord.Client = kargs["client"]
    print(f'{Client.user} has connected to Discord!')

    # Warn if user is not bot
    if not Client.user.bot:
        print("WARNING: The connected account is not a bot, as it is against ToS we do not condone user botting")

    # bot start time check to not reparse timers on network disconnect
    if kargs["bot_start"] > (time.time() - 10):

        with db_hlapi(None) as db:
            mutes: List[Tuple[str, str, str, int]] = db.fetch_all_mutes()
            lost_mutes = sorted(mutes, key=lambda a: a[3])

        ts = datetime_now().timestamp()

        lost_mute_timers = [i for i in lost_mutes if 0 != i[3]]

        if lost_mute_timers:

            print(f"Lost mutes: {len(lost_mute_timers)}")
            for i in lost_mute_timers:
                if i[3] < ts:
                    await attempt_unmute(Client, i)

            lost_mute_timers = [i for i in lost_mute_timers if i[3] >= ts]
            if lost_mute_timers:
                print(f"Mute timers to recover: {len(lost_mute_timers)}\nThis process will end in {round(lost_mutes[-1][3]-time.time())} seconds")

                for i in lost_mute_timers:
                    await asyncio.sleep(i[3] - datetime_now().timestamp())
                    with db_hlapi(int(i[0])) as db:
                        if db.is_muted(infractionid=i[1]):
                            await attempt_unmute(Client, i)

            print("Mutes recovered")


async def on_guild_join(guild: discord.Guild, **kargs: Any) -> None:
    inc_statistics_better(guild.id, "on-guild-join", kargs["kernel_ramfs"])
    with db_hlapi(guild.id) as db:
        db.create_guild_db()


category_info: Dict[str, str] = {'name': 'Initializers'}

commands: Dict[str, Callable[..., Any]] = {"on-ready": on_ready, "on-guild-join": on_guild_join}

version_info: str = "1.2.10"
