import discord
from discord.ext import commands, tasks
from discord_slash import cog_ext, SlashContext
from discord_slash.utils.manage_commands import create_option, create_choice, add_slash_command

import re
from datetime import datetime, date, timedelta, timezone
import aiohttp

from cogs import config

class Site(commands.Cog):
    version_list = []
    public_release_date = datetime.utcfromtimestamp(0)
    patreon_release = None
    previous_activity = ""
    release_dates = ["is very soon™", "is later today", "is tomorrow", "in 3 days", "in 4 days", "in 5 days", "in 6 days", "in 7 days", "in a week"]

    def __init__(self, bot):
        self.bot = bot
        self.updateVersions.start()
        self.updatePatreonStatus.start()

    @cog_ext.cog_slash(name="download", description="Gives a link to download a specific (older) version of Cemu.", options=[
        create_option(name="version", description="Type the Cemu version you want a download link of", option_type=3, required=False)
    ])
    async def downloadLink(self, ctx: SlashContext, version: str):
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
                await ctx.send(content=f"The download link for Cemu {version} is <http://cemu.info/releases/cemu_{version}.zip>")
            else:
                corrected_versions = [
                    ver for ver in self.version_list if ver.startswith(version.rsplit(".", 1)[0])]
                if len(corrected_versions) > 1:
                    await ctx.send(content=f"That version never existed, but did you mean Cemu {corrected_versions[0]}? The download link is <http://cemu.info/releases/cemu_{corrected_versions[0]}.zip>")
                else:
                    await ctx.send(content="Are you from the future, or does this version just not exist yet!")

    async def update_activity(self):
        if len(self.version_list) == 0:
            return

        if self.version_list[0] is not self.patreon_release and datetime.utcnow() < self.public_release_date:
            new_activity = f"Public release {self.release_dates[(self.public_release_date-datetime.utcnow()).days+1]}"
        else:
            new_activity = f"Cemu {self.version_list[0]}"
        if new_activity != self.previous_activity and self.bot.ws:
            await self.bot.change_presence(status=discord.Status.online, activity=discord.Game(name=new_activity))
            self.previous_activity = new_activity

    @tasks.loop(minutes=2)
    async def updateVersions(self):
        async with aiohttp.ClientSession() as session:
            async with session.get("http://cemu.info/changelog.html") as res:
                if res.status == 200:
                    try:
                        for ver in re.finditer(r"v(\d\.\d+\.\d+) +\|", await res.text()):
                            self.version_list.append(ver.group(1))
                        await self.update_activity()
                    except:
                        print("Failed to parse the changelog.html page!")

    @tasks.loop(minutes=2)
    async def updatePatreonStatus(self):
        announcement_channel = self.bot.get_channel(
            config.cfg["announcement_channel"])
        if announcement_channel != None:
            async for message in announcement_channel.history(limit=5):
                if message != None:
                    matches = re.search(
                        r"Cemu (\d\.\d+\.\d+)", message.content)
                    if matches:
                        self.public_release_date = message.created_at + \
                            timedelta(days=7)
                        self.public_release_date.replace(tzinfo=timezone.utc)
                        self.patreon_release = matches.group(1)
                    break
        await self.update_activity()

def setup(bot):
    bot.add_cog(Site(bot))