import discord
from discord.ext import commands
import json
import traceback

from cogs import config

try:
	config.init()
except FileNotFoundError:
	print("Error: config.cfg not found; run setup.py and try again!")
	exit()

# parser isn't a cog but it's in the cogs folder if you want to add commands to it
from cogs.parser import Parser
parse_log = Parser().parse_log

# if you want to add any cogs, put them here
# example: ["cogs.foo", "cogs.bar", ...]
startup_extensions = ["cogs.utility"]

class Cemubot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		# load the specified cogs
		for extension in startup_extensions:
			try:
				self.load_extension(extension)
			except Exception as e:
				exc = f"{type(e).__name__}: {e}"
				print(f"Failed to load extension {extension}\n{exc}")
		with open("misc/title_ids.json", "r", encoding="utf-8") as f:
			self.title_ids = json.load(f)
	async def on_ready(self):
		import _version as v
		print(
f"""
+==============+========+======================+
|   _____      | v{v.__version__} |     _           _    |
|  / ____|     +========+    | |         | |   |
| | |     ___ _ __ ___  _   _| |__   ___ | |_  |
| | |    / _ \ '_ ` _ \| | | | '_ \ / _ \| __| |
| | |___|  __/ | | | | | |_| | |_) | (_) | |_  |
|  \_____\___|_| |_| |_|\__,_|_.__/ \___/ \__| |
+==============================================+
""")
	async def on_message(self, message):
		if 'message.channel.id in config.cfg["parsing_channels"]' and message.attachments:
			for attachment in message.attachments:
				if attachment.filename.endswith(".txt"):
					reply_msg = await message.channel.send("Log detected, parsing...")
					log_data = await attachment.read()
					try:
						await parse_log(log_data, message.channel, reply_msg, self.title_ids)
					except Exception as e:
						await reply_msg.edit(content=f"Error: Couldn't parse log; parser threw {type(e).__name__} exception")
						traceback.print_exc()
			
		await self.process_commands(message)

bot = Cemubot(command_prefix=config.cfg["command_prefix"])
bot.run(config.cfg["bot_token"])