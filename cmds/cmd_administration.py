# Administration commands.
# bredo, 2020

import discord, sqlite3
from datetime import datetime


async def recreate_db(message, args, client, stats, cmds):
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS config (property TEXT PRIMARY KEY, value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS infractions (infractionID INTEGER PRIMARY KEY, userID TEXT, moderatorID 
    TEXT, type TEXT, reason TEXT, timestamp INTEGER)''')
    con.commit()
    con.close()
    await message.channel.send("done (unless something broke)")
    

async def wb_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    word_blacklist = "wsjg0operuyhg0834rjhg3408ghyu3goijwrgp9jgpoeij43p"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return

    if len(args) > 1:
        await message.channel.send("Malformed word blacklist.")
        return
    
    if len(args) == 1:
        word_blacklist = args[0]

    # User is an admin and all arguments are correct. Send to database.
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    # Not sure if the following is PEP8 compliant.
    cur.execute('''
        INSERT INTO config (property, value)
        VALUES (?, ?)
        ON CONFLICT (property) DO UPDATE SET
            value = excluded.value
        WHERE property = ?
    ''', ('word-blacklist', word_blacklist, 'word-blacklist'))

    # Commit new changes and then close connection.
    con.commit()
    con.close()

    await message.channel.send("Word blacklist updated successfully.")


async def inflog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    infraction_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return
    
    if len(args) == 1:
        infraction_log = args[0]

    # User is an admin and all arguments are correct. Send to database.
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    # Not sure if the following is PEP8 compliant.
    cur.execute('''
        INSERT INTO config (property, value)
        VALUES (?, ?)
        ON CONFLICT (property) DO UPDATE SET
            value = excluded.value
        WHERE property = ?
    ''', ('infraction-log', infraction_log, 'infraction-log'))

    # Commit new changes and then close connection.
    con.commit()
    con.close()

    await message.channel.send("Infraction log channel ID updated successfully.")


async def joinlog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    join_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return
    
    if len(args) == 1:
        join_log = args[0]

    # User is an admin and all arguments are correct. Send to database.
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    # Not sure if the following is PEP8 compliant.
    cur.execute('''
        INSERT INTO config (property, value)
        VALUES (?, ?)
        ON CONFLICT (property) DO UPDATE SET
            value = excluded.value
        WHERE property = ?
    ''', ('join-log', join_log, 'join-log'))

    # Commit new changes and then close connection.
    con.commit()
    con.close()

    await message.channel.send("Join log channel ID updated successfully.")


async def msglog_change(message, args, client, stats, cmds):
    # Use original null string for cross-compatibility.
    message_log = "0"

    if not message.author.permissions_in(message.channel).administrator:
        await message.channel.send("Insufficient permissions.")
        return
    
    if len(args) == 1:
        message_log = args[0]

    # User is an admin and all arguments are correct. Send to database.
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    # Not sure if the following is PEP8 compliant.
    cur.execute('''
        INSERT INTO config (property, value)
        VALUES (?, ?)
        ON CONFLICT (property) DO UPDATE SET
            value = excluded.value
        WHERE property = ?
    ''', ('message-log', message_log, 'message-log'))

    # Commit new changes and then close connection.
    con.commit()
    con.close()

    await message.channel.send("Message log channel ID updated successfully.")


category_info = {
    'name': 'administration',
    'pretty_name': 'Administration',
    'description': 'Administration commands.'
}


commands = {
    'recreate-db': {
        'pretty_name': 'recreate-db',
        'description': 'Recreate the database if it doesn\'t exist',
        'execute': recreate_db
    },
    'wb-change': {
        'pretty_name': 'wb-change',
        'description': 'Change word blacklist for this guild.',
        'execute': wb_change
    },
    'message-log': {
        'pretty_name': 'message-log',
        'description': 'Change message log for this guild.',
        'execute': msglog_change
    },
    'infraction-log': {
        'pretty_name': 'infraction-log',
        'description': 'Change infraction log for this guild.',
        'execute': inflog_change
    },
    'join-log': {
        'pretty_name': 'join-log',
        'description': 'Change join log for this guild.',
        'execute': joinlog_change
    }
}
