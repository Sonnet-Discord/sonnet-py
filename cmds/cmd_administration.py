# Administration commands.
# bredo, 2020

import discord, sqlite3


async def recreate_db(message, args, client, stats):
    con = sqlite3.connect(f"datastore/{message.guild.id}.db")
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS config (property TEXT PRIMARY KEY, value TEXT)''')
    cur.execute('''CREATE TABLE IF NOT EXISTS infractions (infractionID INTEGER PRIMARY KEY, userID TEXT, moderatorID 
    TEXT, type TEXT, reason TEXT, timestamp INTEGER)''')
    con.close()
    await message.channel.send("done (unless something broke)")

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
    }
}