from discord.ext import commands
import discord

class MemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.bot.sonic_bot_role in before.roles and before.raw_status != after.raw_status:
            status_chan = self.bot.get_channel(776114750064951296)

            if after.raw_status == "offline":
                await status_chan.send(f"{after.mention} is offline. Please wait; it will be back up soon.")
            elif after.raw_status == "online":
                await status_chan.send(f"{after.mention} is back online.")

def setup(bot):
    bot.add_cog(MemberUpdate(bot))