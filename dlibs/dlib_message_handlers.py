# Dynamic libraries (editable at runtime) for message handling
# Ultrabear 2020

import discord, time
from datetime import datetime
from lib_db_obfuscator import db_hlapi
from lib_loaders import load_message_config
from lib_parsers import parse_blacklist, parse_skip_message, parse_permissions

async def on_reaction_add(reaction, client, ramfs):
    mconf = load_message_config(reaction.message.guild.id, ramfs)

    if bool(int(mconf["starboard-enabled"])) and reaction.emoji == mconf["starboard-emoji"] and reaction.count >= int(mconf["starboard-count"]):
        with db_hlapi(reaction.message.guild.id) as db:
            channel_id = db.grab_config("starboard-channel")
            if channel_id:

                channel = client.get_channel(int(channel_id))
                in_board = db.in_starboard(reaction.message.id)
                if channel and not(in_board):

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
            message_embed.add_field(name="Old Message", value=old_message.content, inline=False)
            message_embed.add_field(name="New Message", value=message.content, inline=False)
            message_embed.set_footer(text=f"Message ID: {message.id}")
            message_embed.timestamp = datetime.utcfromtimestamp(int(time.time()))
            await message_log.send(embed=message_embed)

    # Check against blacklist
    mconf = load_message_config(message.guild.id, ramfs)
    broke_blacklist, infraction_type = parse_blacklist(message, mconf)

    if broke_blacklist:
        try:
            await message.delete()
        except discord.errors.Forbidden:
            pass
        stats = {}
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client, stats, command_modules, ramfs)


async def on_message(message, client, command_modules, command_modules_dict, ramfs):
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
        except discord.errors.Forbidden:
            pass
        await command_modules_dict[mconf["blacklist-action"]]['execute'](message, [int(message.author.id), "[AUTOMOD]", ", ".join(infraction_type), "Blacklist"], client, stats, command_modules, ramfs)

    # Check for antispam 

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
                await command_modules_dict[command]['execute'](message, arguments, client, stats, command_modules, ramfs)
                # Regenerate cache
                if command_modules_dict[command]['cache'] in ["purge", "regenerate"]:
                    ramfs.remove_f(f"datastore/{message.guild.id}.cache.db")
                    if command_modules_dict[command]['cache'] == "regenerate":
                        load_message_config(message.guild.id, ramfs)
        except discord.errors.Forbidden:
            pass # Nothing we can do if we lack perms to speak


commands = {
    "on-message": on_message,
    "on-message-edit": on_message_edit,
    "on-message-delete": on_message_delete,
    "on-reaction-add": on_reaction_add
    }
