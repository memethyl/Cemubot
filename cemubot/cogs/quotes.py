import discord
from discord.ext import commands, tasks
from discord.mentions import AllowedMentions
from discord_slash import cog_ext, SlashContext
from discord_slash.client import SlashCommand
from discord_slash.utils.manage_commands import get_all_commands, remove_slash_command, create_permission, create_option, create_choice

import json
import os
from typing import Dict

from cogs import config

class Quote:
    command = ""
    base_command = ""
    title = ""
    content = ""
    guild = 0
    response_type = "embed"
    addressable = False
    slash_command = None

    def __init__(self, slash : SlashCommand, command : str, base_command : str, guild : int, title : str, content : str, response_type : str, addressable : bool):
        self.command = command
        self.base_command = base_command
        self.guild = guild
        self.title = title
        self.content = content
        self.response_type = response_type
        self.addressable = addressable

        command_options = None
        if addressable:
            command_options = [create_option("user", "User that you want the quote to address", 6, False)]
        
        if base_command:
            self.slash_command = slash.add_subcommand(cmd=self.respond, base=base_command, name=self.command, guild_ids=[self.guild], base_default_permission=True, options=command_options)
        else:
            self.slash_command = slash.add_slash_command(cmd=self.respond, name=self.command, guild_ids=[self.guild], default_permission=True, options=command_options)

    def to_embed(self):
        if self.title:
            return discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), title=self.title, description=self.content)
        else:
            return discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), description=self.content)
    
    def to_message(self):
        if self.title:
            return f"**{self.title}**: {self.content}"
        else:
            return self.content
    
    async def respond(self, ctx: SlashContext, user : discord.Member = None):
        if self.response_type == "embed":
            await ctx.send(embed=self.to_embed(), content=(user.mention if user else None), allowed_mentions=AllowedMentions(users=True))
        elif self.response_type == "text":
            await ctx.send(content=(user.mention if user else "")+self.to_message(), allowed_mentions=AllowedMentions(users=True))
    
    def save(self):
        return {"command": self.command, "base": self.base_command, "guild": self.guild, "title": self.title, "content": self.content, "response_type": self.response_type, "addressable": self.addressable}

    async def remove(self, bot, slash : SlashContext):
        self.slash_command
        del self.slash_command
        # Manual requests are required to remove the synced commands
        syncedCommands = await get_all_commands(bot.user.id, config.bot, slash.guild.id)
        for command in syncedCommands:
            if command["name"] == self.command:
                await remove_slash_command(bot.user.id, config.cfg["bot_token"], slash.guild.id, command["id"])

class Quotes(commands.Cog):
    quotes : Dict[str, Quote] = {}
    bot : discord.Client = None

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Load previous commands
        if os.path.isfile("misc/quotes.json"):
            self.load_quotes_from_file()

        # Make list of roles for each guild that should be able to manage quotes
        guild_ids = []
        permissions_per_guild = {}
        async for guild in self.bot.fetch_guilds():
            guild_ids.append(guild.id)
            permissions_per_guild[guild.id] = []
            for guild_role in await guild.fetch_roles():
                if guild_role.permissions.manage_roles == True:
                    permissions_per_guild[guild.id].append(create_permission(guild_role.id, 1, True))

        # Add manage commands
        self.slash_command = self.bot.slash.add_subcommand(base="quote", base_description="Manages the quotes on this server", guild_ids=guild_ids, base_default_permission=False, base_permissions=permissions_per_guild,
            cmd=self.quote_add, name="add", description="Adds a new quote command.", options=[
                create_option(name="name", description="Name of the new command that you want to add. Can't include any spaces!", option_type=3, required=True),
                create_option(name="title", description="Title of the quote. Use \"None\" if you want to have no title.", option_type=3, required=True),
                create_option(name="description", description="Description of the quote. Supports markdown and $user to make an addressed quote!", option_type=3, required=True),
                create_option(name="type", description="Type of the response", option_type=3, required=True, choices=[create_choice(name="Embed Response", value="embed"), create_choice(name="Text Response", value="text")]),
                create_option(name="parent", description="Name of the parent command where this command name will be nested under.", option_type=3, required=False),
                create_option(name="addressable", description="Should the command have an optional user specifier which when used will mention the given user.", option_type=5, required=False)
            ])
        
        self.slash_command = self.bot.slash.add_subcommand(
            base="quote", base_description="Manages the quotes on this server", guild_ids=guild_ids, base_default_permission=False, base_permissions=permissions_per_guild,
            cmd=self.quote_delete, name="delete", options=[
                create_option(name="command", description="Command that's associated with the quote. Don't include the name of the parent command.", option_type=3, required=True)
            ])
        
        # Sync all the loaded quotes and management commands
        await self.bot.slash.sync_all_commands()
    
    def load_quotes_from_file(self):
        self.quotes = {}
        with open("misc/quotes.json", "r", encoding="utf-8") as f:
            quotesJson = json.load(f)
            for quoteJson in quotesJson:
                self.quotes[quoteJson["command"]] = Quote(self.bot.slash, quoteJson["command"], quoteJson["base"], quoteJson["guild"], quoteJson["title"], quoteJson["content"], quoteJson["response_type"], quoteJson["addressable"])
    
    def save_quotes_to_file(self):
        with open("misc/quotes.json", "w") as f:
            storeCommands = []
            for quote in self.quotes.values():
                storeCommands.append(quote.save())
            json.dump(storeCommands, f, indent="\t")

    async def quote_add(self, ctx: SlashContext, name : str, title: str, description : str, type : str, parent : str = "", addressable : bool = False):
        if " " in name:
            await ctx.send("You can't use spaces in the command names!")
            return
        if title.lower() == "none":
            title = ""
        self.quotes[name] = Quote(self.bot.slash, name.lower(), parent, ctx.guild.id, title, description, type, addressable)
        await self.quotes[name].respond(ctx)
        self.save_quotes_to_file()
        await self.bot.slash.sync_all_commands()

    async def quote_delete(self, ctx: SlashContext, command : str):
        await self.quotes[command].remove(self.bot, ctx)
        del self.quotes[command]
        await ctx.send(content="Successfully deleted the command!")
        self.save_quotes_to_file()
        await self.bot.slash.sync_all_commands(delete_from_unused_guilds=True, delete_perms_from_unused_guilds=True)
    
def setup(bot):
    bot.add_cog(Quotes(bot))