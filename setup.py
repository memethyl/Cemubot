import json

def configure():
    try:
        f = open("cemubot/misc/config.cfg", "x+", encoding="utf-8")
    except FileExistsError:
        f = open("cemubot/misc/config.cfg", "w", encoding="utf-8")
    config = {}
    config["bot_token"] = None
    while not config["bot_token"]:
        config["bot_token"] = input("Please provide a bot token: ")
    config["command_prefix"] = input("Please provide a command prefix (e.g. ^ for ^help) ")
    if not config["command_prefix"]:
        print("No prefix provided; defaulting to ^.")
        config["command_prefix"] = "^"
    config["parsing_channels"] = []
    print("Please provide a comma-separated list of channel IDs of channels you want the bot to parse logs in.")
    print("NOTE: A channel ID is something like 123456789123456789, not #channel-name.")
    channels = input("List goes here: ")
    try:
        config["parsing_channels"] = list(map(lambda x: int(x.replace(' ','')), channels.split(',')))
    except ValueError:
        config["parsing_channels"] = []
    print(f"Your config file now looks like this:\n{json.dumps(config, indent=2)}")
    if input("Is this correct? (y/n) ").lower() == 'n':
        f.close()
        configure()
    else:
        json.dump(config, f, indent=4)
        print("Configuration complete. If the bot still doesn't work, try running setup.py again.")
        f.close()

try:
    open("cemubot/misc/config.cfg", "r", encoding="utf-8").close()
    if input("config.cfg already exists; would you like to re-configure the bot? (y/n) ").lower() == 'y':
        configure()
except FileNotFoundError:
    if input("config.cfg not found; would you like to configure the bot? (y/n) ").lower() == 'y':
        configure()