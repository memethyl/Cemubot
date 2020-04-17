from discord.ext import commands, tasks
import discord
import re
import requests

class Site(commands.Cog):
    version_list = []

    def __init__(self, bot):
        self.bot = bot
        self.updateVersions.start()
    
    @commands.command(name="download", help="Search for the game's compatibility wiki page.", aliases=["dl"])
    async def downloadLink(self, ctx, *, version_hint: str):
        version = None
        if version_hint.lower() == "latest":
            version = self.version_list[0]
        elif version_hint.lower() == "previous":
            version = self.version_list[1]
        else:
            matches = re.search(r"(?:Cemu )?(\d\.\d+\.\d+)[a-z]?", version_hint)
            if matches:
                version = matches.group(1)
        if version:
            if version in self.version_list:
                await ctx.send(content=f"The download link for Cemu {version} is <http://cemu.info/releases/cemu_{version.replace('.', '_')}.zip>")
            else:
                corrected_versions = [ver for ver in self.version_list if ver.startswith(version.rsplit(".", 1)[0])]
                if len(corrected_versions) > 1:
                    await ctx.send(content=f"That version never existed, but did you mean Cemu {corrected_versions[0]}? The download link is <http://cemu.info/releases/cemu_{corrected_versions[0].replace('.', '_')}.zip>")
                else:
                    await ctx.send(content="Are you from the future, or does this version just not exist yet!")

    @tasks.loop(minutes=2)
    async def updateVersions(self):
        req = requests.get("http://cemu.info/changelog.html")
        if req.status_code != 200:
            print("Error: Failed to make a request to Cemu's changelog page.")
            return
        for ver in re.finditer(r"v(\d\.\d+\.\d+) +\|", req.text):
            self.version_list.append(ver.group(1))

def setup(bot):
    bot.add_cog(Site(bot))