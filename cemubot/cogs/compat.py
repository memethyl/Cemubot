from discord.ext import commands
from thefuzz import process
import discord
import urllib.parse
import re

from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option

class Compat(commands.Cog, name="Compatibility Wiki"):
    def __init__(self, bot):
        self.bot = bot
        self.search_dict = dict()
        # create title search set
        for ent in self.bot.title_ids:
            if self.bot.title_ids[ent]["wiki_has_game_id_redirect"] and self.bot.title_ids[ent]["region"] != "JAP":
                simple_name = re.sub(r"[^a-z0-9: ]+", '', self.bot.title_ids[ent]["game_title"].lower()).strip()
                if ':' in simple_name:
                    # make games that have their title prefixed with the game's series searchable
                    self.search_dict[simple_name.split(':')[0].strip()] = self.bot.title_ids[ent]["game_id"]
                    self.search_dict[simple_name.split(':')[1].strip()] = self.bot.title_ids[ent]["game_id"]
                else:
                    self.search_dict[simple_name] = self.bot.title_ids[ent]["game_id"]

    @cog_ext.cog_slash(name="search", description="Search the Cemu compat wiki for the given game's compatibility page.", options=[
        create_option(name="game", description="The name of the game that you want to search for", option_type=3, required=True)
    ])
    async def compatibility(self, ctx : SlashContext, game: str):
        simple_hint = re.sub(r"[^a-z0-9 ]+", '', game.lower())
        guess = process.extractOne(simple_hint, list(self.search_dict.keys()), score_cutoff=60)
        if guess is not None:
            await ctx.send(content=f"The game's compatibility information can be found <https://wiki.cemu.info/wiki/{self.search_dict[guess[0]]}>")
        else:
            await ctx.send(content=f"Couldn't find a good match for the game that you were searching for. Try viewing the compat wiki results <http://wiki.cemu.info/index.php?search={urllib.parse.quote_plus(simple_hint)}>")

def setup(bot):
    bot.add_cog(Compat(bot))