import discord
from discord.ext import commands, tasks
from discord_slash import SlashContext, cog_ext
from discord_slash.context import ComponentContext
from discord_slash.model import BaseCommandObject, ButtonStyle
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.utils.manage_commands import get_all_commands, create_permission, create_option, update_guild_commands_permissions

from cemubot import Cemubot

from cogs import config
from cogs import permissions

class Rules(commands.Cog):
    bot : Cemubot = None

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Change the rules command permissions
        await self.set_rules_permissions()
        self.bot.rules_ready = True
        await self.bot.sync_commands_when_finished()
        permissions.register_update_handler(self.set_rules_permissions)
    
    async def set_rules_permissions(self):
        rules_permissions = {}
        for guild in self.bot.guilds:
            rules_permissions[guild.id] = []

            if guild.id in permissions.role_permissions:
                for role_id in permissions.role_permissions[guild.id]:
                    rules_permissions[guild.id].append(create_permission(role_id, 1, True))
            if guild.id in permissions.user_permissions:
                for user_id in permissions.user_permissions[guild.id]:
                    rules_permissions[guild.id].append(create_permission(user_id, 2, True))
        self.bot.slash.commands["rules"].permissions = rules_permissions
    
    @cog_ext.cog_slash(name="rules", description="Sets the rules in the server and lists the new rules greeting.", default_permission=False, options=[
            create_option(name="rule1", description="Text for rule 1", option_type=3, required=True),
            create_option(name="rule2", description="Text for rule 2", option_type=3, required=True),
            create_option(name="rule3", description="Text for rule 3", option_type=3, required=True),
            create_option(name="rule4", description="Text for rule 4", option_type=3, required=True),
            create_option(name="rule5", description="Text for rule 5", option_type=3, required=True),
            create_option(name="rule6", description="Text for rule 6", option_type=3, required=True)
        ])
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
                create_button(style=ButtonStyle.URL, label="Patreon", url="https://www.patreon.com/cemu"),
                create_button(style=ButtonStyle.URL, label="Setup Guide", url="https://cemu.cfw.guide/"),
                create_button(style=ButtonStyle.URL, label="Discord Invite Link", url="https://discord.gg/5psYsup")
            ])
        ])


def setup(bot):
    bot.add_cog(Rules(bot))