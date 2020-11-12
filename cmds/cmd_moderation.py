# Moderation commands
# bredo, 2020

import discord


async def kick_user(message, client, stats):

    args = message.content.split()

    if not message.author.permissions_in(message.channel).kick_members:
        await message.channel.send("Insufficient permissions.")
        return

    id_to_kick = args[1]

    if args[1].startswith("<@") and args[1].endswith(">"):
        id_to_kick = args[1][2:-1]

    if id_to_kick.startswith("!"):
        id_to_kick = id_to_kick[1:]

    member_to_kick = client.get_user(int(id_to_kick))

    try:
        await member_to_kick.kick()
    except Error as e:
        print(e)


commands = {
    'kick': {
        'pretty_name': 'kick',
        'description': 'Kick a user',
        'execute': kick_user
    }
}
