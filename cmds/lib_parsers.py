# Parsers for message handling
# Ultrabear 2020

import re

def parse_blacklist(message, blacklist):
    # Preset values
    broke_blacklist = False
    infraction_type = []

    # Check message agaist word blacklist
    word_blacklist = blacklist["word-blacklist"]
    if word_blacklist:
        for i in message.content.lower().split(" "):
            if i in word_blacklist:
                broke_blacklist = True
                infraction_type.append("Word")

    # Check message against REGEXP blacklist
    regex_blacklist = blacklist["regex-blacklist"]
    for i in regex_blacklist:
        if re.findall(i, message.content):
            broke_blacklist = True
            infraction_type.append("RegEx")

    # Check against filetype blacklist
    filetype_blacklist = blacklist["filetype-blacklist"]
    if filetype_blacklist and message.attachments:
        for i in message.attachments:
            for a in filetype_blacklist:
                if i.filename.lower().endswith(a):
                    broke_blacklist = True
                    infraction_type.append("FileType")

    return (broke_blacklist, infraction_type)


# Parse if we skip a message due to X reasons
def parse_skip_message(Client, message):

    # Make sure we don't start a feedback loop.
    if message.author == Client.user:
        return True

    # Ignore message if author is a bot
    if message.author.bot:
        return True

    return False