# Constants cause discord likes to troll us
# Ultrabear 2021


class message:
    content: int = 2000


class embed:

    title: int = 256
    description: int = 2048
    author: int = 256

    class field:
        name: int = 256
        value: int = 1024

    footer: int = 2048


class sonnet:
    error_embed = "ERROR: The bot does not have permissions to send embeds here"
