# Joke commands idk mck wanted this
# Ultrabear 2020

import discord

from typing import Any, List


async def joke_ban_user(message: discord.Message, args: List[str], client: discord.Client, **kwargs: Any) -> Any:

    reason: str = " ".join(args[1:])[:1024] if len(args) > 1 else "No Reason Specified"

    try:
        user = client.get_user(int(args[0].strip("<@!>")))
    except ValueError:
        user = None
    except IndexError:
        await message.channel.send("No user specified")
        return 1

    if not user:
        await message.channel.send(f"'Banned' {args[0]} for {reason}", allowed_mentions=discord.AllowedMentions.none())
    else:
        await message.channel.send(f"'Banned' {user.mention} with ID {user.id} for {reason}", allowed_mentions=discord.AllowedMentions.none())


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

version_info: str = "1.2.3-DEV"
