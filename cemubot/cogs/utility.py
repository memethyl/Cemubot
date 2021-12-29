from discord.ext import commands
import discord
import json
import re
import requests
import traceback

class Utility(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(help="Updates the bot's title ID database. You must have the \"Manage Roles\" permission to run this command.")
	@commands.has_guild_permissions(manage_roles=True)
	async def update_db(self, ctx):
		reply_msg = await ctx.channel.send("Updating title ID database...")
		try:
			self.update_title_ids()
			await reply_msg.edit(content="Successfully updated title ID database.")
		except Exception as e:
			await reply_msg.edit(content=f"Error: Couldn't update title ID database; threw {type(e).__name__} exception")
			traceback.print_exc()

	def update_title_ids(self):
		session = requests.Session()

		def validate_req(req):
			if req.status_code != 200:
				raise requests.HTTPError(f"Error: request to {req.url} returned {req.status_code}")

		# continue_key is the API argument that allows you to continue from a certain point in the search
		# `&list=categorymembers` has `cmcontinue`, `&generator=allredirects` has `garcontinue`, etc.
		# just read the mediawiki API docs for whatever endpoint you're using and look for an argument that says:
		# "When more results are available, use this to continue."
		def get_all_results(req, continue_key, api_url):
			req_json = json.loads(req.text)
			try:
				req_json["continue"][continue_key]
			except KeyError:
				return req_json
			while req_json["continue"][continue_key]:
				new_req = session.get(f"{api_url}&{continue_key}={req_json['continue'][continue_key]}")
				validate_req(new_req)
				new_req = json.loads(new_req.text)
				try:
					req_json["query"][list(req_json["query"].keys())[0]].extend(new_req["query"][list(new_req["query"].keys())[0]])
				except AttributeError:
					req_json["query"][list(req_json["query"].keys())[0]].update(new_req["query"][list(new_req["query"].keys())[0]])
				try:
					req_json["continue"] = new_req["continue"]
				except KeyError:
					break
			return req_json

		game_info = session.get("http://wiiubrew.org/w/api.php?action=parse&format=json&page=Title_database&section=6&prop=wikitext")
		validate_req(game_info)
		game_info = json.loads(game_info.text)
		game_info = game_info["parse"]["wikitext"]["*"]
		game_info = re.findall(r"\| ([0-9A-Fa-f]{8}-[0-9A-Fa-f]{8})\n\|(?: |)(.*?)(?: |)\n\|(?: |)(.*?)\n\|(?: |)(.*?)\n\|(?: |)(.*?)\n\|(?: |)(.*?)\n\|(?: |)(.*?)\n\|(?: |)(.*?)\n\|(?:-\n|)",
								game_info)
		game_info = [list(x) for x in game_info]
		temp = {}
		for item in game_info:
			item[2] = item[2].replace(' ','')
			item[3] = item[3].replace(' ','')
			temp[item[0].upper()] = {
				"game_title": item[1],
				"game_id": item[2][-4:]+(item[3][-2:] if item[3] != '-' else ''),
				"product_code": item[2],
				"company_code": item[3],
				"notes": item[4],
				"versions": item[5],
				"region": item[6],
				"cdn_available": item[7]
			}
		game_info = temp

		# see which game IDs the wiki actually has
		wiki_game_ids = session.get("http://wiki.cemu.info/api.php?action=query&format=json&generator=allredirects&garlimit=5000")
		validate_req(wiki_game_ids)
		wiki_game_ids = get_all_results(wiki_game_ids, "garcontinue", wiki_game_ids.url)
		temp = {}
		for pageid in wiki_game_ids["query"]["pages"].keys():
			temp[pageid] = wiki_game_ids["query"]["pages"][pageid]["title"]
		wiki_game_ids = temp
		wiki_game_ids = [x for x in wiki_game_ids.values() if re.findall(r"^[A-Za-z0-9]{4,6}$", x)]

		for key in game_info.copy().keys():
			game_info[key]["wiki_has_game_id_redirect"] = (game_info[key]["game_id"] in wiki_game_ids)

		self.bot.title_ids = game_info
		try:
			f = open("misc/title_ids.json", "w", encoding="utf-8")
		except FileNotFoundError:
			f = open("misc/title_ids.json", "x+", encoding="utf-8")
		json.dump(game_info, f, indent=4)
		f.close()

def setup(bot):
	bot.add_cog(Utility(bot))