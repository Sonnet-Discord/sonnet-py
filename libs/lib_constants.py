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

    error_embed: str = "ERROR: The bot does not have permissions to send embeds here"

    class error_args:
        not_enough: str = "ERROR: Not enough args supplied"

    class error_channel:
        none: str = "ERROR: No channel supplied"
        invalid: str = "ERROR: Channel is not a valid channel"
        scope: str = "ERROR: Channel is not in guild"

    class error_role:
        none: str = "ERROR: No role supplied"
        invalid: str = "ERROR: Role is not valid role"

    class error_message:
        invalid: str = "ERROR: Message does not exist"

