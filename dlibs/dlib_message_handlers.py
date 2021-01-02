# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import importlib

import discord, time, asyncio
from datetime import datetime

import lib_db_obfuscator; importlib.reload(lib_db_obfuscator)
import lib_parsers; importlib.reload(lib_parsers)
import lib_loaders; importlib.reload(lib_loaders)

from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config, directBinNumber
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions


async def on_reaction_add(reaction, client, ramfs):

    # Skip if not a guild
    if not reaction.message.guild:
        return

    mconf = load_message_config(reaction.message.guild.id, ramfs)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        with db_hlapi(reaction.message.guild.id) as db:
            if channel_id := db.grab_config("starboard-channel"):
                if bool(channel := client.get_channel(int(channel_id))) and not(db.in_starboard(reaction.message.id)) and not(channel_id == reaction.message.channel):

                    db.add_to_starboard(reaction.message.id)
                    jump = f"\n\n[(Link)]({reaction.message.jump_url})"
                    starboard_embed = discord.Embed(title="Starred message",description=reaction.message.content[: 2048 - len(jump)] + jump, color=0xffa700)
                    starboard_embed.set_author(name=reaction.message.author, icon_url=reaction.message.author.avatar_url)
                    starboard_embed.timestamp = datetime.utcnow()

                    await channel.send(embed=starboard_embed)


async def on_message_delete(message, client):

    # Ignore bots
    if parse_skip_message(client, message):
        return

    # Add to log
    with db_hlapi(message.guild.id) as db:
       message_log = db.grab_config("message-log")
    if message_log:
        message_log = client.get_channel(int(message_log))
        if message_log:
            message_embed = discord.Embed(title=f"Message deleted in #{message.channel}", description=message.content, color=0xd62d20)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcnow()

            await message_log.send(embed=message_embed)


async def on_message_edit(old_message, message, client, command_modules, command_modules_dict, ramfs):

    # Ignore bots
    if parse_skip_message(client, message):
        return

    # Add to log
    with db_hlapi(message.guild.id) as db:
       message_log = db.grab_config("message-log")
    if message_log:
        message_log = client.get_channel(int(message_log))
        if message_log:
            message_embed = discord.Embed(title=f"Message edited in #{message.channel}", color=0xffa700)
            message_embed.set_author(name=f"{message.author} ({message.author.id})", icon_url=message.author.avatar_url)
            message_embed.add_field(name="Old Message", value=(old_message.content or "NULL"), inline=False)
            message_embed.add_field(name="New Message", value=(message.content or "NULL"), inline=False)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcfromtimestamp(int(time.time()))
            await message_log.send(embed=message_embed)

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, infraction_type = parse_blacklist(message, mconf)

    if broke_blacklist:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        stats = {}
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client)


def antispam_check(guildid, userid, ramfs, **kargs):
    messagecount = kargs["messages"]
    timecount = kargs["time"]*1000
    try:
        messages = ramfs.read_f(f"antispam/{guildid}.cache.asam")
        messages.seek(0)
        droptime = round(time.time()*1000) - timecount
        userlist = []
        ismute = 1

        while a := messages.read(16):
            uid = int.from_bytes(a[:8], "little")
            mtime = int.from_bytes(a[8:], "little")
            if mtime > droptime:
                userlist.append([uid, mtime])
                if uid == userid:
                    ismute += 1

        userlist.append([userid, round(time.time()*1000)])
        messages.seek(0)
        for i in userlist:
            messages.write(bytes(directBinNumber(i[0], 8) + directBinNumber(i[1], 8)))
        messages.truncate()
        if ismute > messagecount:
            return True
        else:
            return False

    except FileNotFoundError:
        messages = ramfs.create_f(f"antispam/{guildid}.cache.asam")
        messages.write(bytes(directBinNumber(userid, 8) + directBinNumber(round(time.time()*1000), 8)))
        return False


async def on_message(message, client, command_modules, command_modules_dict, ramfs, bot_start_time, main_version_info):
    # Statistics.
    stats = {"start": round(time.time() * 100000), "end": 0}

    if parse_skip_message(client, message):
        return

    # Load message conf
    stats["start-load-blacklist"] = round(time.time() * 100000)
    mconf = load_message_config(message.guild.id, ramfs)
    stats["end-load-blacklist"] = round(time.time() * 100000)

    # Check message against blacklist
    stats["start-blacklist"] = round(time.time() * 100000)
    broke_blacklist, infraction_type = parse_blacklist(message, mconf)
    stats["end-blacklist"] = round(time.time() * 100000)

    # If blacklist broken generate infraction
    if broke_blacklist:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client)

    # Check for antispam
    stats["start-antispam"] = round(time.time() * 100000)
    spammer = (antispam_check(message.channel.guild.id, message.author.id, ramfs, messages=3, time=2))
    stats["end-antispam"] = round(time.time() * 100000)

    if spammer:
        try:
            await message.delete()
        except (discord.errors.Forbidden, discord.errors.NotFound):
            pass
        with db_hlapi(message.guild.id) as db:
            if not db.is_muted(userid=message.author.id):
                await command_modules_dict["mute"]['execute'](message, ["20s", int(message.author.id), "[AUTOMOD]",  "Antispam"], client)

    # Check if this is meant for us.
    if not message.content.startswith(mconf["prefix"]):
        return

    # Split into cmds and arguments.
    arguments = message.content.split()
    command = arguments[0][len(mconf["prefix"]):]

    # Remove command from the arguments.
    del arguments[0]

    # Process commands
    if command in command_modules_dict.keys():
        permission = await parse_permissions(message, command_modules_dict[command]['permission'])
        try:
            if permission:
                stats["end"] = round(time.time() * 100000)
                await command_modules_dict[command]['execute'](message, arguments, client, stats=stats, cmds=command_modules, ramfs=ramfs, bot_start=bot_start_time, dlib_version=version_info, main_version=main_version_info)
                # Regenerate cache
                if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
                    ramfs.remove_f(f"datastore/{message.guild.id}.cache.db")
                    if command_modules_dict[command]['cache'] == "regenerate":
                        load_message_config(message.guild.id, ramfs)
        except discord.errors.Forbidden:
            pass # Nothing we can do if we lack perms to speak


async def attempt_unmute(Client, mute_entry):

    with db_hlapi(mute_entry[0]) as db:
        db.unmute_user(infractionid=mute_entry[1])
        mute_role = db.grab_config("mute-role")
    guild = Client.get_guild(int(mute_entry[0]))
    if guild and mute_role:
        user = guild.get_member(int(mute_entry[2]))
        mute_role = guild.get_role(int(mute_role))
        if user and mute_role:
            try:
                await user.remove_roles(mute_role)
            except discord.errors.Forbidden:
                pass


async def on_ready(Client, bot_start_time):
    print(f'{Client.user} has connected to Discord!')

    # Warn if user is not bot
    if not Client.user.bot:
        print("WARNING: The connected account is not a bot, as it is against ToS we do not condone user botting")
    
    # bot start time check to not reparse timers on network disconnect
    if bot_start_time > (time.time()-10):

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
                    await attempt_unmute(Client, i)

            print("Mutes recovered")


async def on_guild_join(guild):
    with db_hlapi(guild.id) as db:
        db.create_guild_db()


async def on_raw_reaction_add(payload, client, ramfs):
    pass # ENDPOINT FOR SONNET 1.1.0


commands = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    "on-reaction-add": on_reaction_add,
    "on-raw-reaction-add": on_raw_reaction_add,
    "on-ready": on_ready,
    "on-guild-join": on_guild_join
    }


version_info = "1.0.2-DEV_editnull"
