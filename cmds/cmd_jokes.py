# Joke commands idk mck wanted this
# Ultrabear & atrt7 2021


async def joke_ban_user(message, args, client, **kwargs):

    if len(args) > 1:
        reason = " ".join(args[1:])
    else:
        reason = "No Reason Specified"

    try:
        user = client.get_user(int(args[0].strip("<@!>")))
    except ValueError:
        await message.channel.send("Invalid User")
        return
    except IndexError:
        await message.channel.send("No user specified")
        return

    await message.channel.send(f"'Banned' {user.mention} with ID {user.id} for {reason}")

async def h_command(message, args, client, **kwargs):

    await message.channel.send("h lmao haha funny I said h now laugh")

category_info = {'name': 'jokes', 'pretty_name': 'Jokes', 'description': 'Joke commands, because because'}

commands = {
    'jban': {
        'pretty_name': 'jban <uid>',
        'description': '"bans" a user',
        'permission': 'moderator',
        'cache': 'keep',
        'execute': joke_ban_user
        },
    'h': {
        'pretty_name': 'h',
        'description': 'h',
        'permission': 'everyone',
        'cache': 'keep',
        'execute': h_command
    }
}

version_info = "1.1.4-DEV"
