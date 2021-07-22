import discord
from discord import channel
from discord.ext import commands

import typing
import os
import json


user_permissions : typing.Dict[int, typing.List[int]] = {}
role_permissions : typing.Dict[int, typing.List[int]] = {}

handlers : typing.List[typing.Coroutine] = []
def register_update_handler(handler_func : typing.Coroutine):
    handlers.append(handler_func)

async def trigger_update_event():
    for callback in handlers:
        await callback()

class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        if os.path.isfile("misc/permissions.json"):
            self.load_permissions_from_file()
    
    def load_permissions_from_file(self):
        with open("misc/permissions.json", "r", encoding="utf-8") as f:
            all_permissions = json.load(f)
            for permission in all_permissions["users"]:
                user_permissions[int(permission)] = all_permissions["users"][permission]
            for permission in all_permissions["roles"]:
                role_permissions[int(permission)] = all_permissions["roles"][permission]
    
    async def save_permissions_to_file(self):
        with open("misc/permissions.json", "w") as f:
            json.dump({"users": user_permissions, "roles": role_permissions}, f, indent="\t")

    @commands.command(group="permissions", name="grant", help="Allows you to grant permission to a member or role for the quote commands.")
    @commands.has_guild_permissions(manage_guild=True)
    async def permissions_grant(self, ctx : commands.Context, role_or_member: typing.Union[discord.Role, discord.Member]):
        if isinstance(role_or_member, discord.Role):
            role_permissions.setdefault(ctx.guild.id, [])
            if not role_or_member.id in role_permissions[ctx.guild.id]:
                role_permissions[ctx.guild.id].append(role_or_member.id)
        elif isinstance(role_or_member, discord.Member):
            user_permissions.setdefault(ctx.guild.id, [])
            if not role_or_member.id in user_permissions[ctx.guild.id]:
                user_permissions[ctx.guild.id].append(role_or_member.id)
        await self.save_permissions_to_file()
        await trigger_update_event()
        await ctx.reply(content="Granted the permission!")
    
    @commands.command(group="permissions", name="revoke", help="Allows you to revoke a granted permission to a member or role for the quote commands.")
    @commands.has_guild_permissions(manage_guild=True)
    async def permissions_revoke(self, ctx : commands.Context, role_or_member: typing.Union[discord.Role, discord.Member]):
        if isinstance(role_or_member, discord.Role):
            if ctx.guild.id in role_permissions and role_or_member.id in role_permissions[ctx.guild.id]:
                role_permissions[ctx.guild.id].remove(role_or_member.id)
        elif isinstance(role_or_member, discord.Member):
            if ctx.guild.id in user_permissions and role_or_member.id in user_permissions[ctx.guild.id]:
                user_permissions[ctx.guild.id].remove(role_or_member.id)
        await self.save_permissions_to_file()
        await trigger_update_event()
        await ctx.reply(content="Removed the permission!")

def setup(bot):
    bot.add_cog(Permissions(bot))
