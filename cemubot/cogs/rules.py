import discord
from discord.ext import commands, tasks
from discord_slash import SlashContext
from discord_slash.context import ComponentContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.utils.manage_commands import get_all_commands, create_permission, create_option, update_guild_commands_permissions

import os
from cemubot import Cemubot

from cogs import config
from cogs import permissions

class Rules(commands.Cog):
    bot : Cemubot = None

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        guild_ids = []
        async for guild in self.bot.fetch_guilds():
            guild_ids.append(guild.id)

        # Add the rules command
        self.bot.slash.add_slash_command(cmd=self.change_rules, name="rules", description="Sets the rules in the server and lists the new rules greeting.", guild_ids=guild_ids, default_permission=False, options=[
                create_option(name="rule1", description="Text for rule 1", option_type=3, required=True),
                create_option(name="rule2", description="Text for rule 2", option_type=3, required=True),
                create_option(name="rule3", description="Text for rule 3", option_type=3, required=True),
                create_option(name="rule4", description="Text for rule 4", option_type=3, required=True),
                create_option(name="rule5", description="Text for rule 5", option_type=3, required=True),
                create_option(name="rule6", description="Text for rule 6", option_type=3, required=True)
            ])
        await self.bot.slash.sync_all_commands()

        await self.set_rules_permissions()
        permissions.register_update_handler(self.set_rules_permissions)
    
    async def set_rules_permissions(self):
        # Make and set list of permissions set for each guild, then update the permissions of the roles command
        async for guild in self.bot.fetch_guilds():
            guild_permissions = []

            if guild.id in permissions.role_permissions:
                for role_id in permissions.role_permissions[guild.id]:
                    guild_permissions.append(create_permission(role_id, 1, True))
            if guild.id in permissions.user_permissions:
                for user_id in permissions.user_permissions[guild.id]:
                    guild_permissions.append(create_permission(user_id, 2, True))

            # Manual requests to update the permissions for the already synced commands
            command_permissions = []
            syncedCommands = await get_all_commands(self.bot.user.id, config.cfg["bot_token"], guild.id)
            for command in syncedCommands:
                if command["name"] == "rules":
                    command_permissions.append({"id": command["id"], "permissions": guild_permissions})
                    break
            await update_guild_commands_permissions(self.bot.user.id, config.cfg["bot_token"], guild.id, command_permissions)

    async def change_rules(self, ctx: SlashContext, rule1, rule2, rule3, rule4, rule5, rule6):
        quotes_cog = self.bot.get_cog("Quotes")
        if quotes_cog:
            await quotes_cog.quote_edit(ctx, name="r1", description=rule1)
            await quotes_cog.quote_edit(ctx, name="r2", description=rule2)
            await quotes_cog.quote_edit(ctx, name="r3", description=rule3)
            await quotes_cog.quote_edit(ctx, name="r4", description=rule4)
            await quotes_cog.quote_edit(ctx, name="r5", description=rule5)
            await quotes_cog.quote_edit(ctx, name="r6", description=rule6)

        rules_embed = discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), title="Welcome to the official Cemu Discord Server!", description="Please try to respect the following server rules, or you'll be warned or banned.",)

        rules_embed.set_author(name="Server Rules", icon_url=str(ctx.guild.icon_url_as(static_format="png")))
        rules_embed.add_field(name="Rule 1", value=rule1, inline=False)
        rules_embed.add_field(name="Rule 2", value=rule2, inline=False)
        rules_embed.add_field(name="Rule 3", value=rule3, inline=False)
        rules_embed.add_field(name="Rule 4", value=rule4, inline=False)
        rules_embed.add_field(name="Rule 5", value=rule5, inline=False)
        rules_embed.add_field(name="Rule 6", value=rule6, inline=False)

        resource_embed = discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), description="After reading our rules, check out these useful resources that'll help you to start playing your games using Cemu!")

        await ctx.send(embeds=[rules_embed, resource_embed], components=[
            create_actionrow(*[
                create_button(style=ButtonStyle.URL, label="Cemu.info Website", url="https://cemu.info/"),
                create_button(style=ButtonStyle.URL, label="Compatibility Wiki", url="https://wiki.cemu.info/wiki/Main_Page"),
                create_button(style=ButtonStyle.URL, label="Cemu Setup Guide", url="https://cemu.cfw.guide/"),
                create_button(style=ButtonStyle.URL, label="Discord Invite Link", url="https://discord.gg/5psYsup")
            ])
        ])


def setup(bot):
    bot.add_cog(Rules(bot))