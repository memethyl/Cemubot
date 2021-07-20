import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
import json
import requests
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
startup_extensions = ["cogs.utility", "cogs.compat", "cogs.site", "cogs.quotes"]

class Cemubot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

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
	def load_cogs(self):
		# load the specified cogs
		for extension in startup_extensions:
			try:
				self.load_extension(extension)
			except Exception as e:
				exc = f"{type(e).__name__}: {e}"
				print(f"Failed to load extension {extension}\n{exc}")
				traceback.print_exc()
	async def on_message(self, message):
		if message.author.id == self.user.id:
			return
		for embed in message.embeds:
			if not embed.url or not embed.title:
				continue
			if '://pastebin.com/' in embed.url and ('Init Cemu' in embed.title or 'Outdated graphic pack' in embed.title):
				if message.channel.id == config.cfg["parsing_channel"]["preferred"] \
				or message.channel.id in config.cfg["parsing_channel"]["alternates"] \
				or not config.cfg["parsing_channel"]["preferred"]:
					embed.url = embed.url.replace(".com/", ".com/raw/")
					log_data = requests.get(embed.url).content
					reply_msg = await message.channel.send("Log detected, parsing...")
					try:
						await parse_log(embed.url, log_data, message.channel, reply_msg, self.title_ids)
					except Exception as e:
						await reply_msg.edit(content=f"Error: Couldn't parse log; parser threw {type(e).__name__} exception")
						traceback.print_exc()
		for attachment in message.attachments:
			log_data = await attachment.read()
			if attachment.filename.endswith(".txt") and b"Init Cemu" in log_data:
				if message.channel.id == config.cfg["parsing_channel"]["preferred"] \
				or message.channel.id in config.cfg["parsing_channel"]["alternates"] \
				or not config.cfg["parsing_channel"]["preferred"]:
					reply_msg = await message.channel.send("Log detected, parsing...")
					try:
						await parse_log(attachment.url, log_data, message.channel, reply_msg, self.title_ids)
					except Exception as e:
						await reply_msg.edit(content=f"Error: Couldn't parse log; parser threw {type(e).__name__} exception")
						traceback.print_exc()
				else:
					await message.channel.send(f"Log detected, please post logs in <#{config.cfg['parsing_channel']['preferred']}>.")

		await self.process_commands(message)

if __name__ == '__main__':
	intents = discord.Intents.none()
	intents.guilds = True
	intents.messages = True
	intents.dm_messages = True

	bot = Cemubot(command_prefix=config.cfg["command_prefix"], intents=intents)
	bot.slash = SlashCommand(client=bot, sync_commands=True, sync_on_cog_reload=True, override_type=True)
	bot.load_cogs()
	bot.run(config.cfg["bot_token"])