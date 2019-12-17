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
    print("Please provide the channel ID of the channel(s) you want the bot to parse logs in.")
    print("NOTE: A channel ID is something like 123456789123456789, not #channel-name.")
    config["parsing_channel"] = {}
    config["parsing_channel"]["preferred"] = int(input("Preferred channel ID goes here (0 to parse in all channels): "))
    config["parsing_channel"]["alternates"] = list(map(int, input("Comma-separated list of IDs goes here (leave blank to skip): ").split(',')))
    config["compatibility_colors"] = {
        "perfect": 0x3380CC,
        "playable": 0x16A689,
        "runs": 0xD9D936,
        "loads": 0xDF8D12,
        "unplayable": 0xBF3E32,
        "unknown": 0x858585
    }
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