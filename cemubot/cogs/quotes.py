from cemubot import Cemubot
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from typing import Any, Callable, Coroutine, Dict, Literal, Optional, TypedDict
import discord
import json


class Quote:
    name: str = ""
    guild_id: Optional[int] = None
    title: str = ""
    content: str = ""
    response_type: Literal["embed", "text"] = "embed"
    addressable: bool = False

    def __init__(self, name: str,
                 guild_id: Optional[int], title: str,
                 content: str, response_type: str, addressable: bool):
        self.name = name
        self.guild_id = guild_id
        self.title = title
        self.content = content.replace("\\n", "\n")
        self.response_type = response_type
        self.addressable = addressable

    def to_embed(self) -> discord.Embed:
        if self.title:
            return discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), title=self.title, description=self.content)
        else:
            return discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), description=self.content)

    def to_message(self) -> str:
        if self.title:
            return f"**{self.title}**: {self.content}"
        else:
            return self.content

    async def respond(self, inter: discord.Interaction) -> None:
        if self.response_type == "embed":
            await inter.response.send_message(embed=self.to_embed(),
                allowed_mentions=discord.AllowedMentions(users=True))
        else:
            await inter.response.send_message(content=self.to_message(),
                allowed_mentions=discord.AllowedMentions(users=True))

    async def respond_addressable(self, inter: discord.Interaction, user: Optional[discord.Member]=None) -> None:
        if self.response_type == "embed":
            await inter.response.send_message(embed=self.to_embed(), content=(user.mention if user else None),
                allowed_mentions=discord.AllowedMentions(users=True))
        else:
            await inter.response.send_message(content=(user.mention if user else None)+self.to_message(),
                allowed_mentions=discord.AllowedMentions(users=True))

    def save(self) -> dict:
        return {
            "name": self.name,
            "guild_id": self.guild_id,
            "title": self.title,
            "content": self.content,
            "response_type": self.response_type,
            "addressable": self.addressable
        }


class QuoteExtras(TypedDict):
    quote: Quote


class QuoteContainer:
    command: app_commands.Command

    def __init__(self, command: app_commands.Command):
        self.command = command

    @property
    def quote(self) -> Optional[Quote]:
        if not self.command.extras:
            return None
        return self.command.extras["quote"]

    @quote.setter
    def quote(self, value: Quote) -> None:
        if not self.command.extras:
            self.command.extras = {}
        self.command.extras["quote"] = value


class Quotes(commands.GroupCog, name="quote", description="Manages the quotes on this server"):
    quotes: Dict[str, QuoteContainer] = {}
    bot: Cemubot

    def __init__(self, bot: Cemubot) -> None:
        self.bot = bot
        super().__init__()

    @commands.GroupCog.listener()
    async def on_ready(self):
        self.load_quotes()
        self.bot.quotes_ready = True
        await self.bot.sync_commands_when_finished()

    def load_quotes(self) -> None:
        try:
            with open("misc/quotes.json", "r", encoding="utf-8") as file:
                quotes = json.load(file)
            for quote in quotes:
                self._add_command(Quote(quote["name"], quote["guild_id"], quote["title"],
                        quote["content"], quote["response_type"], quote["addressable"]))
        except FileNotFoundError:
            pass

    def save_quotes(self) -> None:
        with open("misc/quotes.json", "w", encoding="utf-8") as file:
            json.dump([quote.quote.save() for quote in self.quotes.values()], file, indent=4)

    def _add_command(self, quote: Quote) -> app_commands.Command:
        keys = quote.name.split(" ")
        group = self.bot.tree
        for key in keys[:-1]:
            temp = group.get_command(key)
            if temp:
                subgroup = temp
            else:
                subgroup = app_commands.Group(name=key, description="No description.")
                group.add_command(subgroup)
            group = subgroup
        command = app_commands.Command(name=keys[-1], description=quote.title,
            callback=quote.respond_addressable if quote.addressable else quote.respond,
            extras=QuoteExtras(quote=quote))
        group.add_command(command)
        self.quotes[quote.name] = QuoteContainer(command)
        return command

    @app_commands.command(name="add", description="Adds a new quote command.")
    @app_commands.describe(
        name="Name of the command you want to add.",
        content="Contents of the quote. Supports markdown!",
        title="Title of the quote. Use \"None\" if you want to have no title.",
        type="Type of the response (embed or text)",
        addressable="Should the command have an optional user specifier which when used will mention the given user.")
    @app_commands.choices(type=[
        Choice(name="Embed Response", value="embed"),
        Choice(name="Text Response", value="text")])
    @app_commands.guild_only()
    async def add(self, inter: discord.Interaction, name: str, title: str, content: str,
        type: Choice[str], addressable: bool = False) -> None:
        if title.lower() == "none":
            title = ""
        for quote_name in self.quotes.keys():
            if name == quote_name:
                await inter.response.send_message("That command already exists.")
                return
            elif quote_name.startswith(name+" "):
                await inter.response.send_message("That command already exists as a group. Due to Discord limitations, groups are not invokable.")
                return
        quote = Quote(name, inter.guild_id, title, content, type.value, addressable)
        self._add_command(quote)
        self.save_quotes()
        await inter.response.defer(thinking=True)
        await self.bot.tree.sync()
        if quote.response_type == "embed":
            await inter.followup.send(embed=quote.to_embed(),
                allowed_mentions=discord.AllowedMentions(users=True))
        else:
            await inter.followup.send(content=quote.to_message(),
                allowed_mentions=discord.AllowedMentions(users=True))

    async def quote_edit(self, name: str, field: str, new_value: str,
        respond_func: Optional[Callable[..., Coroutine[Any, Any, Any]]]=None) -> bool:
        async def _noop_coro(*args, **kwargs):
            pass
        if not respond_func:
            respond_func = _noop_coro
        if name not in self.quotes:
            await respond_func(f"Couldn't edit {name} command since it doesn't exist!")
            return False
        if field.lower() == "title":
            self.quotes[name].quote.title = new_value if new_value != "None" else ""
        elif field.lower() == "content":
            self.quotes[name].quote.content = new_value.replace("\\n", '\n')
        elif field.lower() == "type":
            if (new_value != "embed") and (new_value != "text"):
                await respond_func("You can only set the quote type to either 'embed' or 'text'.")
                return False
            else:
                self.quotes[name].quote.response_type = new_value
        else:
            await respond_func("That's not a valid thing you can edit. You can only edit 'title', 'content' or 'type'.")
            return False
        await respond_func("Successfully edited the quote!")
        self.save_quotes()
        return True

    @app_commands.command(name="edit",
        description="Edits certain properties of a quote. Requires the \"Manage Roles\" permission.")
    @app_commands.describe(
        name="Name of the quote to edit.",
        field="Field of the internal structure to edit.",
        new_value="New value of the field.")
    @app_commands.checks.has_permissions(manage_roles=True)
    @app_commands.guild_only()
    async def edit(self, inter: discord.Interaction, name: str, field: str, new_value: str):
        async def _respond_func(content: str):
            await inter.response.send_message(content=content)
        self.quote_edit(name, field, new_value, _respond_func)

    @app_commands.command(name="delete", description="Deletes an existing quote command. Also works on groups.")
    @app_commands.describe(name="Name of the command to delete.")
    @app_commands.guild_only()
    async def delete(self, inter: discord.Interaction, name: str) -> None:
        for cmd in self.bot.tree.walk_commands():
            if cmd.qualified_name == name:
                (cmd.parent or self.bot.tree).remove_command(cmd.name)
                break
        else:
            await inter.response.send_message(content="Couldn't find a quote with that name.")
            return
        quotes_to_remove = [] # avoids RuntimeError
        for quote in map(lambda x: x.quote, self.quotes.values()):
            if quote.name.startswith(cmd.qualified_name):
                quotes_to_remove.append(quote.name)
        for quote_name in quotes_to_remove:
            del self.quotes[quote_name]
        self.save_quotes()
        await inter.response.defer(thinking=True)
        await self.bot.tree.sync()
        await inter.followup.send(content="Successfully deleted the command!")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Quotes(bot))