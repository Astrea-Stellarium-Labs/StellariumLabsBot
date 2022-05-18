import importlib

import dis_snek

import common.utils as utils


class MemberUpdate(dis_snek.Scale):
    def __init__(self, bot):
        self.bot: dis_snek.Snake = bot
        self.personal_bot_role: dis_snek.Role = self.bot.cache.get_role(
            775913721092374528
        )

    @dis_snek.listen("presence_update")
    async def on_presence_update(self, event: dis_snek.events.PresenceUpdate):
        if event.guild_id == 775912554928144384:
            member = self.bot.get_member(event.user.id, 775912554928144384)

            if member.has_role(self.personal_bot_role):
                await utils.msg_to_owner(self.bot, event.client_status)

                status_chan = self.bot.get_channel(952033760931610624)

                if event.client_status == "offline":
                    await status_chan.send(
                        f"{event.user.mention} is offline. Please wait - this tends to"
                        " happen semi-frequently, and the bot will come back up soon"
                        " automatically."
                    )

                elif event.client_status == "online" and event.activities:
                    # this more or less checks if a bot actually has an activity, which bots like
                    # Seraphim will have only when they are done
                    await status_chan.send(f"{event.user.mention} is back online.")


def setup(bot):
    importlib.reload(utils)
    MemberUpdate(bot)
