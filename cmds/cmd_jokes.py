# Joke commands idk mck wanted this
# Ultrabear 2020


async def joke_ban_user(message, args, client, **kwargs):

    if len(args) > 1:
        reason = " ".join(args[1:])
    else:
        reason = "No Reason Specified"

    try:
        user = client.get_user(int(args[0].strip("<@!>")))
    except ValueError:
        user = None
    except IndexError:
        await message.channel.send("No user specified")
        return

    if not user:
        await message.channel.send(f"'Banned' {user} for {reason}")
    else:
        await message.channel.send(f"'Banned' {user.mention} with ID {user.id} for {reason}")


category_info = {'name': 'jokes', 'pretty_name': 'Jokes', 'description': 'Joke commands, because because'}

commands = {
    'jkb': {
        'pretty_name': 'jkb <uid>',
        'description': '"bans" a user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': joke_ban_user
        },
    }

version_info = "1.1.6-DEV"
