import datetime
import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
import json
import requests
import time
import traceback

# parser isn't a cog but it's in the cogs folder if you want to add commands to it
from cogs.parser import ExtraParser, RulesetParser

# if you want to add any cogs, put them here
# example: ["cogs.foo", "cogs.bar", ...]
startup_extensions = ["cogs.permissions", "cogs.utility", "cogs.compat", "cogs.site", "cogs.quotes", "cogs.rules"]


class Cemubot(commands.Bot):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		with open("misc/title_ids.json", "r", encoding="utf-8") as f:
			self.title_ids = json.load(f)
		with open("misc/rulesets.json", "r", encoding="utf-8") as f:
			self.rulesets = json.load(f)
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
	quotes_ready = False
	rules_ready = False
	async def sync_commands_when_finished(self):
		if self.quotes_ready and self.rules_ready:
			await self.slash.sync_all_commands()
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
						await self.parse_log(embed.url, log_data, reply_msg)
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
						await self.parse_log(attachment.url, log_data, reply_msg)
					except Exception as e:
						await reply_msg.edit(content=f"Error: Couldn't parse log; parser threw {type(e).__name__} exception")
						traceback.print_exc()
				else:
					await message.channel.send(f"Log detected, please post logs in <#{config.cfg['parsing_channel']['preferred']}>.")
		await self.process_commands(message)
	
	async def parse_log(self, log_url, log, message, title_ids=None):
		if title_ids == None:
			title_ids = self.title_ids
		try:
			log = log.decode('utf-8').replace('\r', '')
		except UnicodeDecodeError:
			# brazilian portugese was causing problems
			log = log.decode('latin-1').replace('\r', '')
		parser = ExtraParser(title_ids)
		info = parser.parse(log)
		if not info["init.loaded_title"]:
			if info["init.game_crashed"]:
				if info["init.piracy_check"]:
					await message.edit(content="Error: Cemu crashed before loading the game. This was caused by bad game files.")
				elif info["init.overwolf_issue"]:
					await message.edit(content="Error: Cemu crashed before loading the game. This was caused by Overwolf.")
				else:
					await message.edit(content="Error: Cemu crashed before loading the game. Try making sure that you're using the latest GPU drivers.")
			else:
				await message.edit(content="Error: No game detected. Submit a log during or after emulating a game. Reopening Cemu clears the log.")
			return
		ruleset_parser = RulesetParser(self.rulesets)
		relevant_info = ruleset_parser.parse(log, info)
		relevant_info += [
			f"ℹ RPX hash (updated): `{info['game.rpx_hash.updated']}` ║ RPX hash (base): `{info['game.rpx_hash.base']}`"
		]
		# TODO: reimplement "Some information was not found"
		await message.edit(content=None, embed=self.create_embed(log_url, info, relevant_info))
	
	def create_embed(self, log_url: str, info: dict, relevant_info: list=["N/A"]) -> discord.Embed:
		try:
			game_title = self.title_ids[info["game.title_id"]]["game_title"]
		except KeyError:
			game_title = None
		if info["game.compat.rating"] != "Unknown":
			description = f"Tested as **{info['game.compat.rating']}** on {info['game.compat.version']}"
		else:
			description = "No known compatibility rating yet"
		# i saw a couple of tests where the rating wasn't one of the standard five,
		# so i'm putting this in a try-except block just in case
		try:
			colour = config.cfg["compatibility_colors"][info["game.compat.rating"].lower()]
		except KeyError:
			colour = config.cfg["compatibility_colors"]["unknown"]
		embed = discord.Embed(colour=discord.Colour(colour),
							  title=info["game.title_id"]+(" ("+game_title+")" if game_title else ""),
							  url=(info["game.wiki_page.url"] or log_url),
							  description=description,
							  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
		# TODO: omit unknown info?
		opengl_using = ""
		vulkan_using = ""
		if info["specs.gfx_api_version"] != "Unknown":
			if info["settings.backend"] == "OpenGL":
				opengl_using = f" (using {info['specs.gfx_api_version']})"
			elif info["settings.backend"] == "Vulkan":
				vulkan_using = f" (using {info['specs.gfx_api_version']})"
		game_emu_info = ''.join((
f"**Cemu:** {info['emulator.cemu_version']}\n",
f"**Cemuhook:** {info['emulator.cemuhook_version']}\n",
f"**Title version:** {info['game.title_version']}\n",
f"[View full log](https://docs.google.com/a/cdn.discordapp.com/viewer?url={log_url})"
))
		specs = ''.join((
f"**CPU:** {info['specs.cpu']}\n",
f"**RAM:** {info['specs.ram']}MB\n",
f"**GPU:** [{info['specs.gpu']}]({info['specs.gpu_specs.url']})\n",
f"**GPU driver:** {info['specs.gpu_driver']}\n",
f"**OpenGL:** {info['specs.opengl']}{opengl_using} ║ **Vulkan:** {info['specs.vulkan']}{vulkan_using}"
))
		settings = ''.join((
f"**CPU mode:** {info['settings.cpu_mode']}\n",
f"**CPU affinity:** `{info['settings.cpu_affinity']}`\n",
f"**Graphics backend:** {info['settings.backend']}\n",
f"{('**Async compile:** '+info['settings.vulkan_async']+chr(10)) if info['settings.vulkan_async'] != 'N/A' else ''}",
f"{('**Accurate barriers:** '+info['settings.accurate_barriers']+chr(10)) if info['settings.accurate_barriers'] != 'N/A' else ''}",
f"**Full sync at GX2DrawDone:** {info['settings.gx2drawdone']}\n",
f"**Custom timer mode:** {info['settings.custom_timer_mode']}"
))
		embed.add_field(name="Game/Emulator Info", value=game_emu_info, inline=True)
		embed.add_field(name="Specs", value=specs, inline=True)
		embed.add_field(name="Settings", value=settings, inline=False)
		embed.add_field(name="Relevant Info", value='\n'.join(relevant_info), inline=False)
		return embed


if __name__ == '__main__':
	# initialize config
	from cogs import config
	try:
		config.init()
	except FileNotFoundError:
		print("Error: config.cfg not found; run setup.py and try again!")
		exit()

	# initialize discord and slash commands instances
	intents = discord.Intents.none()
	intents.guilds = True
	intents.messages = True
	intents.dm_messages = True

	bot = Cemubot(command_prefix=config.cfg["command_prefix"], intents=intents)
	bot.slash = SlashCommand(client=bot)
	bot.load_cogs()
	bot.run(config.cfg["bot_token"])