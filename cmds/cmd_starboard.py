# Starboard system
# Ultrabear 2020

from lib_parsers import parse_boolean, update_log_channel
from lib_mdb_handler import db_handler
from sonnet_cfg import STARBOARD_EMOJI

async def starboard_channel_change(message, args, client, stats, cmds, ramfs):
    try:
        await update_log_channel(message, args, client, "archive-channel")
    except RuntimeError:
        return


async def set_starboard_emoji(message, args, client, stats, cmds, ramfs):

    if args:
        emoji = args[0]
    else:
        emoji = STARBOARD_EMOJI

    with db_handler() as database:
        database.add_to_table(f"{message.guild.id}_config",[["property", "starboard-emoji"],["value", emoji]])

    await message.channel.send(f"Updated starboard emoji to {emoji}")


async def set_starboard_use(message, args, client, stats, cmds, ramfs):

    if args:
        gate = parse_boolean(args[0])
    else:
        gate = False

    with db_handler() as database:
        database.add_to_table(f"{message.guild.id}_config",[["property", "starboard-enabled"],["value", int(gate)]])

    await message.channel.send(f"Starboard set to {bool(gate)}")


async def set_starboard_count(message, args, client, stats, cmds, ramfs):

    if args:
        try:
            count = int(float(args[0]))
        except ValueError:
            await message.channel.send("Invalid input, please enter a number")
            return
    else:
        await message.channel.send("No input")
        return

    with db_handler() as database:
        database.add_to_table(f"{message.guild.id}_config",[["property","starboard-count"],["value",count]])

    await message.channel.send(f"Updated starboard count to {count}")


category_info = {
    'name': 'starboard',
    'pretty_name': 'Starboard',
    'description': 'Starboard commands.'
}


commands = {
    'starboard-channel': {
        'pretty_name': 'starboard-channel',
        'description': 'Change Starboard for this guild.',
        'permission':'administrator',
        'cache':'keep',
        'execute': starboard_channel_change
    },
    'starboard-emoji': {
        'pretty_name': 'starboard-emoji',
        'description': 'Set the starboard emoji',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': set_starboard_emoji
    },
    'starboard-enabled': {
        'pretty_name': 'starboard-enabled',
        'description': 'Toggle starboard on or off',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': set_starboard_use
    },
    'starboard-count': {
        'pretty_name': 'starboard-count',
        'description': 'Set starboard reaction count',
        'permission':'administrator',
        'cache':'regenerate',
        'execute': set_starboard_count
    }        
}
