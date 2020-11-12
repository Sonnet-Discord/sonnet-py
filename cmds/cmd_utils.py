# Utility Commands
# Funey, 2020

# Predefined dictionaries.

import discord


async def ping_function(message, client, stats):
    embed = discord.Embed(title="Pong!", description="Connection between Sonnet and Discord is OK", color=0x00ff6e)
    embed.add_field(name="Process Time", value=str(stats["end"] - stats["start"]) + "ms", inline=False)
    await message.channel.send(embed=embed)


commands = {
    'ping': {
        'pretty_name': 'ping',
        'description': 'Ping bot.',
        'execute': ping_function
    }
}
