from discord.ext import commands
import discord

class MemberUpdate(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if self.bot.sonic_bot_role in before.roles:
            status_chan = self.bot.get_channel(776114750064951296)

            if before.activities != after.activities:
                # yes, this is important to check - if a bot goes offline, it loses its activities
                # and when a bot gets back online, it gets back its activities

                if before.raw_status != after.raw_status and after.raw_status == "offline":
                    await status_chan.send(f"{after.mention} is offline. Please wait - this tends to happen semi-frequently" +
                    ", and the bot will come back up soon automatically.")

                elif after.raw_status == "online" and after.activities != ():
                    # this more or less checks if a bot actually has an activity, which bots like
                    # Seraphim will have only when they are done
                    await status_chan.send(f"{after.mention} is back online.")

def setup(bot):
    bot.add_cog(MemberUpdate(bot))