from cemubot import Cemubot
from cogs import config
from discord import app_commands
from discord.ext import commands
import discord


class Rules(commands.Cog):
    bot: Cemubot

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.rules_ready = True
        await self.bot.sync_commands_when_finished()

    @app_commands.command(name="rules", description="Sets the rules in the server and lists the new rules greeting.")
    @app_commands.describe(
        r1="Text for rule 1",
        r2="Text for rule 2",
        r3="Text for rule 3",
        r4="Text for rule 4",
        r5="Text for rule 5",
        r6="Text for rule 6")
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def rules(self, inter: discord.Interaction, r1: str, r2: str, r3: str, r4: str, r5: str, r6: str):
        await inter.response.defer()
        quotes_cog = self.bot.get_cog("Quotes")
        if quotes_cog:
            await quotes_cog.quote_edit("r1", "content", r1)
            await quotes_cog.quote_edit("r2", "content", r2)
            await quotes_cog.quote_edit("r3", "content", r3)
            await quotes_cog.quote_edit("r4", "content", r4)
            await quotes_cog.quote_edit("r5", "content", r5)
            await quotes_cog.quote_edit("r6", "content", r6)
        
        rules_embed = discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), title="Welcome to the official Cemu Discord Server!", description="Please try to respect the following server rules, or you'll be warned or banned.")
        rules_embed.set_author(name="Server Rules", icon_url=str(inter.guild.icon.with_static_format("png")))
        rules_embed.add_field(name="Rule #1", value=r1, inline=False)
        rules_embed.add_field(name="Rule #2", value=r2, inline=False)
        rules_embed.add_field(name="Rule #3", value=r3, inline=False)
        rules_embed.add_field(name="Rule #4", value=r4, inline=False)
        rules_embed.add_field(name="Rule #5", value=r5, inline=False)
        rules_embed.add_field(name="Rule #6", value=r6, inline=False)
        
        resource_embed = discord.Embed(colour=discord.Colour.from_rgb(0, 162, 221), description="After reading our rules, check out these useful resources that'll help you to start playing your games using Cemu!")
        component_view = discord.ui.View()                                                                                                       \
            .add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Cemu.info Website", url="https://cemu.info/"))                     \
            .add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Compatibility Wiki", url="https://wiki.cemu.info/wiki/Main_Page")) \
            .add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Patreon", url="https://www.patreon.com/cemu"))                     \
            .add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Setup Guide", url="https://cemu.cfw.guide/"))                      \
            .add_item(discord.ui.Button(style=discord.ButtonStyle.url, label="Discord Invite Link", url="https://discord.gg/5psYsup"))
        
        await inter.followup.send(embeds=(rules_embed, resource_embed), view=component_view)


async def setup(bot: commands.Bot):
    await bot.add_cog(Rules(bot))