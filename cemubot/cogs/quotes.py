import discord
from discord.ext import commands, tasks
from discord.mentions import AllowedMentions
from discord_slash import cog_ext, SlashContext
from discord_slash.client import SlashCommand
from discord_slash.model import SubcommandObject
from discord_slash.utils.manage_commands import get_all_commands, remove_slash_command, create_permission, create_option, create_choice, update_guild_commands_permissions

import json
import os
from typing import Dict
from cemubot import Cemubot

from cogs import config
from cogs import permissions

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

        command_options = []
        if self.addressable == True:
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
        # Manual requests are required to remove the synced commands
        syncedCommands = await get_all_commands(bot.user.id, config.cfg["bot_token"], slash.guild.id)
        for command in syncedCommands:
            if command["name"] == self.command:
                await remove_slash_command(bot.user.id, config.cfg["bot_token"], slash.guild.id, command["id"])
                del bot.slash.commands[command["name"]]
            elif command["name"] == self.base_command:
                await remove_slash_command(bot.user.id, config.cfg["bot_token"], slash.guild.id, command["id"])
                del bot.slash.commands[command["name"]]
        del self.slash_command
        self.slash_command = None

class Quotes(commands.Cog):
    quotes : Dict[str, Quote] = {}
    bot : Cemubot = None

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Load previous commands
        if os.path.isfile("misc/quotes.json"):
            self.load_quotes_from_file()

        # Set the manage commands permissions and sync if it's fully done
        await self.set_quote_permissions()
        self.bot.quotes_ready = True
        await self.bot.sync_commands_when_finished()
        permissions.register_update_handler(self.set_quote_permissions)

    async def set_quote_permissions(self):
        quote_permissions = {}
        for guild in self.bot.guilds:
            quote_permissions[guild.id] = []

            if guild.id in permissions.role_permissions:
                for role_id in permissions.role_permissions[guild.id]:
                    quote_permissions[guild.id].append(create_permission(role_id, 1, True))
            if guild.id in permissions.user_permissions:
                for user_id in permissions.user_permissions[guild.id]:
                    quote_permissions[guild.id].append(create_permission(user_id, 2, True))
        self.bot.slash.commands["quote"].permissions = quote_permissions

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
    
    @cog_ext.cog_subcommand(base="quote", base_description="Manages the quotes on this server", base_default_permission=False,
        name="add", description="Adds a new quote command.", options=[
            create_option(name="name", description="Name of the new command that you want to add. Can't include any spaces!", option_type=3, required=True),
            create_option(name="title", description="Title of the quote. Use \"None\" if you want to have no title.", option_type=3, required=True),
            create_option(name="description", description="Description of the quote. Supports markdown!", option_type=3, required=True),
            create_option(name="type", description="Type of the response", option_type=3, required=True, choices=[create_choice(name="Embed Response", value="embed"), create_choice(name="Text Response", value="text")]),
            create_option(name="parent", description="Name of the parent command where this command name will be nested under.", option_type=3, required=False),
            create_option(name="addressable", description="Should the command have an optional user specifier which when used will mention the given user.", option_type=5, required=False)
        ])
    async def quote_add(self, ctx: SlashContext, name : str, title: str, description : str, type : str, parent : str = "", addressable : bool = False):
        if " " in name:
            await ctx.send("You can't use spaces in the command names!", hidden=True)
            return
        if title.lower() == "none":
            title = ""
        await ctx.defer()
        self.quotes[name] = Quote(self.bot.slash, name.lower(), parent, ctx.guild.id, title, description, type, addressable)
        self.save_quotes_to_file()
        await self.bot.slash.sync_all_commands()
        await self.quotes[name].respond(ctx)
    
    # Could make this command visible once Discord's command system actually hides commands properly
    async def quote_edit(self, ctx: SlashContext, name : str = None, title : str = None, description : str = None, type : str = None):
        if name not in self.quotes:
            await ctx.send(f"Couldn't edit {name} command since it doesn't exist!", hidden=True)
            return
        if title is not None:
            self.quotes[name].title = name if name == "None" else ""
        if description is not None:
            self.quotes[name].content = description
        if type is not None and (type == "embed" or type == "text"):
            self.quotes[name].type = type
        self.save_quotes_to_file()
    
    @cog_ext.cog_subcommand(base="quote", base_description="Manages the quotes on this server", base_default_permission=False,
        name="delete", description="Deletes an existing quote command.", options=[
            create_option(name="command", description="Deletes a parent command.", option_type=3, required=True)
        ])
    async def quote_delete(self, ctx: SlashContext, command : str):
        has_parent = False
        matched_command = False
        matched_parent = False
        parent_children = []
        for quote in self.quotes:
            if self.quotes[quote].command == command:
                matched_command = True
                if self.quotes[quote].base_command:
                    has_parent = True
            if self.quotes[quote].base_command == command:
                matched_parent = True
                parent_children.append(self.quotes[quote].command)
        
        # Check for some edge cases
        if not matched_command and not matched_parent:
            await ctx.send(content="Couldn't find a quote with that name.", hidden=True)
        if matched_command and matched_parent:
            await ctx.send(content="It seems like there's both a parent and a command with the same name. Deleting the command with no parents.", hidden=True)
            matched_parent = False
        if has_parent:
            await ctx.send(content="You can't delete a command that is under a parent. Deleting the parent will delete all it's children", hidden=True)
            return
        
        # Delete (parent) command
        await ctx.defer()
        if matched_parent and not matched_command:
            # Delete single command
            await self.quotes[parent_children[0]].remove(self.bot, ctx)
            for child_quote in parent_children:
                del self.quotes[child_quote]
        else:
            await self.quotes[command].remove(self.bot, ctx)
            del self.quotes[command]
        await ctx.send(content="Successfully deleted the command!")
        self.save_quotes_to_file()
        await self.bot.slash.sync_all_commands()
    
def setup(bot):
    bot.add_cog(Quotes(bot))