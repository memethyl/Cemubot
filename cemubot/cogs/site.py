import discord
from discord import app_commands
from discord.ext import commands, tasks

import re
from datetime import datetime, date, timedelta, timezone
import aiohttp

from cogs import config

class Site(commands.Cog):
    bot : discord.Client = None
    version_list = []
    previous_activity = ""

    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        await self.getAllVersions.start()
        await self.getLatestVersion.start()

    @app_commands.command(name="download", description="Gives a link to download a specific (older) version of Cemu.")
    @app_commands.describe(version="The Cemu version that you want to download.")
    async def download(self, inter: discord.Interaction, version: str):
        if version.lower() == "latest":
            version = self.version_list[0]
        elif version.lower() == "previous":
            version = self.version_list[1]
        else:
            matches = re.search(r"(?:Cemu )?(\d\.\d+\.\d+)[a-z]?", version)
            if matches:
                version = matches.group(1)
        if version:
            if version in self.version_list:
                await inter.response.send_message(content=f"The download link for Cemu {version} is <http://cemu.info/releases/cemu_{version}.zip>")
            else:
                corrected_versions = [
                    ver for ver in self.version_list if ver.startswith(version.rsplit(".", 1)[0])]
                if len(corrected_versions) > 1:
                    await inter.response.send_message(
                        content=f"That version never existed, but did you mean Cemu {corrected_versions[0]}? The download link is <http://cemu.info/releases/cemu_{corrected_versions[0]}.zip>")
                else:
                    await inter.response.send_message(
                        content="Are you from the future, or does this version just not exist yet?!")

    async def update_activity(self, version):
        new_activity = f"Cemu {version}"
        if new_activity != self.previous_activity and self.bot.ws:
            await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(name=new_activity))
            self.previous_activity = new_activity

    @tasks.loop(minutes=2.0)
    async def getLatestVersion(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://cemu.info/api/cemu_version3.php") as res:
                if res.status == 200:
                    try:
                        text = await res.text()
                        for ver in re.finditer(r"cemu_(\d+\.\d+\.\d+).zip", text):
                            await self.update_activity(ver.group(1))
                    except Exception as err:
                        print("Failed to parse the /api/cemu_version3.php page! Error:")
                        print(str(err))

    @tasks.loop(minutes=10.0)
    async def getAllVersions(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://cemu.info/changelog.html") as res:
                if res.status == 200:
                    try:
                        text = await res.text()
                        for ver in re.finditer(r"v(\d+\.\d+\.\d+) +\|", text):
                            self.version_list.append(ver.group(1))
                    except Exception as err:
                        print("Failed to parse the changelog.html page! Error:")
                        print(str(err))

async def setup(bot):
    await bot.add_cog(Site(bot))