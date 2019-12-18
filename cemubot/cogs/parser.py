import datetime
from discord.ext import commands
import discord
import re
import requests
import time

from cogs import config

class Parser():
	def __init__(self):
		self.file = None
		self.channel = None
		self.embed = None

	async def parse_log(self, file, channel, reply_msg, title_ids):
		self.file = file.decode('utf-8').replace('\r', '')
		self.channel = channel
		self.reply_msg = reply_msg
		self.title_ids = title_ids
		self.embed = {
			"emu_info": {},
			"game_info": {},
			"specs": {},
			"settings": {},
			"relevant_info": []
		}
		if not re.search(r"------- Init Cemu .*? -------", self.file, re.M):
			await self.reply_msg.edit(content="Error: This is not a Cemu log file.")
			return
		elif not re.search(r"------- Loaded title -------", self.file, re.M):
			await self.reply_msg.edit(content="Error: No game detected. Run Cemu again and play a game.")
			return
		
		self.detect_emu_info()
		self.detect_specs()
		self.detect_settings()
		self.get_relevant_info()
		
		await self.reply_msg.edit(content=None, embed=self.create_embed())

	def detect_emu_info(self):
		self.embed["emu_info"]["cemu_version"] = re.search(r"------- Init Cemu (.*?) -------", self.file, re.M).group(1)
		try:
			self.embed["emu_info"]["cemuhook_version"] = re.search(r"Cemuhook version: (.*?)$", self.file, re.M).group(1)
		except AttributeError:
			self.embed["emu_info"]["cemuhook_version"] = "N/A"
		self.embed["game_info"]["title_id"] = re.search(r"TitleId: (.*?)$", self.file, re.M).group(1).upper()
		self.embed["game_info"]["title_version"] = re.search(r"TitleVersion: v([0-9]+)", self.file, re.M).group(1)

		self.embed["game_info"]["wiki_page"] = ""
		if self.title_ids[self.embed["game_info"]["title_id"]]["wiki_has_game_id_redirect"]:
			self.embed["game_info"]["wiki_page"] = f"http://wiki.cemu.info/wiki/{self.title_ids[self.embed['game_info']['title_id']]['game_id']}"
		else:
			# todo: use a cache of the cemu wiki instead of making a request on each parse
			title = self.title_ids[self.embed['game_info']['title_id']]['game_title']
			title = re.sub(r'[^\x00-\x7f]', r'', title)
			title = title.replace(' ', '_')
			self.embed["game_info"]["wiki_page"] = f"http://wiki.cemu.info/wiki/{title}"

		# experimental, probably buggy
		self.embed["game_info"]["compatibility"] = {
			"rating": "Unknown",
			"version": "N/A"
		}
		if self.embed["game_info"]["wiki_page"]:
			compat = requests.get(self.embed["game_info"]["wiki_page"])
			if compat.status_code == 200:
				try:
					# pArSiNg hTmL wItH rEgEx iS a bAd iDeA
					compat = re.findall(r"<tr style=\"vertical-align:middle;\">.*?</tr>", compat.text, re.M|re.S)[-1]
					self.embed["game_info"]["compatibility"] = {
						"rating": re.search(r"<a href=\"/wiki/Category:.*?_\(Rating\)\" title=\"Category:.*? \(Rating\)\">(.*?)</a>", compat).group(1),
						"version": re.search(r"<a href=\"(?:/wiki/|/index\.php\?title=)Release.*? title=\".*?\">(.*?)</a>", compat).group(1)
					}
				except (IndexError, AttributeError):
					pass
			else:
				self.embed["game_info"]["wiki_page"] = ""

	def detect_specs(self):
		self.embed["specs"]["cpu"] = re.search(r"CPU: (.*?) *$", self.file, re.M).group(1)
		self.embed["specs"]["ram"] = re.search(r"RAM: ([0-9]+)MB", self.file, re.M).group(1)
		self.embed["specs"]["gpu"] = re.search(r"(?:GL_RENDERER: |Using GPU: )(.*?)$", self.file, re.M).group(1)
		try:
			self.embed["specs"]["gpu_driver"] = re.search(r"GL_VERSION: (.*?)$", self.file, re.M).group(1)
		except AttributeError:
			self.embed["specs"]["gpu_driver"] = "Unknown"
	
	def detect_settings(self):
		self.embed["settings"]["cpu_mode"] = re.search(r"CPU-Mode: (.*?)$", self.file, re.M).group(1)
		self.embed["settings"]["cpu_extensions"] = re.search(r"Recompiler initialized. CPU extensions: (.*?)$", self.file, re.M).group(1)
		enabled_cpu_extensions = ' '.join(re.findall(r"CPU extensions that will actually be used by recompiler: (.*?)$", self.file, re.M))
		self.embed["settings"]["disabled_cpu_extensions"] = set()
		if enabled_cpu_extensions:
			self.embed["settings"]["disabled_cpu_extensions"] = {x for x in re.findall(r"(\b\w*\b)", self.embed["settings"]["cpu_extensions"], re.M)} \
															- {x for x in re.findall(r"(\b\w*\b)", enabled_cpu_extensions, re.M) if x}
		self.embed["settings"]["backend"] = ("OpenGL" if "OpenGL" in self.file else "Vulkan")
		self.embed["settings"]["gx2drawdone"] = ("Enabled" if "Full sync at GX2DrawDone: true" in self.file else "Disabled")
		self.embed["settings"]["console_region"] = re.search(r"Console region: (.*?)$", self.file, re.M).group(1)
		self.embed["settings"]["thread_quantum"] = (None if "Thread quantum set to " not in self.file else re.search(r'Thread quantum set to (.*?)$', self.file, re.M).group(1))
		try:
			self.embed["settings"]["custom_timer_mode"] = re.search(r"Custom timer mode: (.*?)$", self.file, re.M).group(1)
		except AttributeError:
			self.embed["settings"]["custom_timer_mode"] = "none"
		if self.embed["settings"]["custom_timer_mode"] == "none":
			self.embed["settings"]["custom_timer_mode"] = "Default"
	
	def get_relevant_info(self):
		if self.embed["emu_info"]["cemuhook_version"] == "N/A":
			self.embed["relevant_info"] += ["❓ Cemuhook is not installed"]
		if int(self.embed["specs"]["ram"])-8000 < 0:
			self.embed["relevant_info"] += ["⚠️ Less than 8 GB of RAM"]
		if self.embed["settings"]["cpu_mode"] == "Single-core interpreter":
			self.embed["relevant_info"] += ["⚠️ CPU mode is set to Single-core interpreter"]
		if self.embed["settings"]["disabled_cpu_extensions"] and self.embed["emu_info"]["cemuhook_version"] != "N/A":
			self.embed["relevant_info"] += [f"❓ These CPU extensions are disabled: `{', '.join([x for x in self.embed['settings']['disabled_cpu_extensions'] if x])}`"]
		if "Intel" in self.embed["specs"]["gpu"]:
			self.embed["relevant_info"] += ["⚠️ Intel GPUs are not officially supported due to poor performance"]
		if self.embed["settings"]["console_region"] != "Auto":
			self.embed["relevant_info"] += [f"🤔 Console region set to {self.embed['settings']['console_region']}"]
		if self.embed["settings"]["thread_quantum"]:
			self.embed["relevant_info"] += [f"🤔 Thread quantum set to {self.embed['settings']['thread_quantum']} (non-default value)"]
		if "Radeon" in self.embed["specs"]["gpu"] and self.embed["settings"]["backend"] == "OpenGL":
			self.embed["relevant_info"] += ["⚠️ AMD GPUs and OpenGL go together like oil and water; use Vulkan if possible"]
		
	def create_embed(self):
		game_title = self.title_ids[self.embed["game_info"]["title_id"]]["game_title"]
		if self.embed["game_info"]["compatibility"]["rating"] != "Unknown":
			description = f"**{self.embed['game_info']['compatibility']['rating']}** since {self.embed['game_info']['compatibility']['version']}"
		else:
			description = "Unknown compatibility rating"
		# i saw a couple of tests where the rating wasn't one of the standard five,
		# so i'm putting this in a try-except block just in case
		try:
			colour = config.cfg["compatibility_colors"][self.embed["game_info"]["compatibility"]["rating"].lower()]
		except KeyError:
			colour = config.cfg["compatibility_colors"]["unknown"]
			
		embed = discord.Embed(colour=discord.Colour(colour), 
							  title=self.embed["game_info"]["title_id"]+(" ("+game_title+")" if game_title else " (Unknown title)"),
							  url=(self.embed["game_info"]["wiki_page"] or None),
							  description=description,
							  timestamp=datetime.datetime.utcfromtimestamp(time.time()))
		game_emu_info = f"""
Cemu {self.embed['emu_info']['cemu_version']}
Cemuhook {self.embed['emu_info']['cemuhook_version']}
**Title version:** v{self.embed['game_info']['title_version']}
"""
		specs = f"""
**CPU:** {self.embed['specs']['cpu']}
**RAM:** {self.embed['specs']['ram']}MB
**GPU:** {self.embed['specs']['gpu']}
**GPU driver:** {self.embed['specs']['gpu_driver']}
"""
		settings = f"""
**CPU mode:** {self.embed['settings']['cpu_mode']}
**Graphics backend:** {self.embed['settings']['backend']}
**Full sync at GX2DrawDone:** {self.embed['settings']['gx2drawdone']}
**Custom timer mode:** {self.embed["settings"]["custom_timer_mode"]}
"""
		if not self.embed["relevant_info"]:
			self.embed["relevant_info"] = ["N/A"]
		embed.add_field(name="Game/Emulator Info", value=game_emu_info, inline=True)
		embed.add_field(name="Specs", value=specs, inline=True)
		embed.add_field(name="Settings", value=settings, inline=False)
		embed.add_field(name="Relevant Info", value='\n'.join(self.embed["relevant_info"]), inline=False)
		return embed