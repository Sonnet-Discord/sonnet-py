# Handlers for initializing the bot and guilds
# Ultrabear 2021

import importlib

import discord, time, asyncio

import lib_db_obfuscator

importlib.reload(lib_db_obfuscator)

from lib_db_obfuscator import db_hlapi

from typing import Dict, Callable, Any, List


async def attempt_unmute(Client: discord.Client, mute_entry: List[Any]):

    with db_hlapi(mute_entry[0]) as db:
        db.unmute_user(infractionid=mute_entry[1])
        mute_role_id = db.grab_config("mute-role")

    if (guild := Client.get_guild(int(mute_entry[0]))) and mute_role_id:
        if (user := guild.get_member(int(mute_entry[2]))) and (mute_role := guild.get_role(int(mute_role_id))):
            try:
                await user.remove_roles(mute_role)
            except discord.errors.Forbidden:
                pass


async def on_ready(**kargs: Any) -> None:
    Client: discord.Client = kargs["client"]
    print(f'{Client.user} has connected to Discord!')

    # Warn if user is not bot
    if not Client.user.bot:
        print("WARNING: The connected account is not a bot, as it is against ToS we do not condone user botting")

    # bot start time check to not reparse timers on network disconnect
    if kargs["bot_start"] > (time.time() - 10):

        with db_hlapi(None) as db:
            lost_mutes = sorted(db.fetch_all_mutes(), key=lambda a: a[3])

        if lost_mutes:

            print(f"Lost mutes: {len(lost_mutes)}")
            for i in lost_mutes:
                if time.time() > i[3]:
                    await attempt_unmute(Client, i)

            lost_mute_timers = [i for i in lost_mutes if time.time() < i[3]]
            if lost_mute_timers:
                print(f"Mute timers to recover: {len(lost_mute_timers)}\nThis process will end in {round(lost_mutes[-1][3]-time.time())} seconds")

                for i in lost_mute_timers:
                    await asyncio.sleep(i[3] - time.time())
                    with db_hlapi(i[0]) as db:
                        if db.is_muted(infractionid=i[1]):
                            await attempt_unmute(Client, i)

            print("Mutes recovered")


async def on_guild_join(guild, **kargs):
    with db_hlapi(guild.id) as db:
        db.create_guild_db()


category_info: Dict[str, str] = {'name': 'Initializers'}

commands: Dict[str, Callable] = {"on-ready": on_ready, "on-guild-join": on_guild_join}

version_info: str = "1.2.3-DEV"
