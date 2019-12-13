# this file exists so that every .py file can share the same config variable
# if you want to use the config variable in another file,
# add "from cogs import config" to that file

import json

def init():
	global cfg
	with open("misc/config.cfg", "r", encoding="utf-8") as f:
		cfg = json.load(f)