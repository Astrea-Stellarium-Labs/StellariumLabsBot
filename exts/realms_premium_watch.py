import asyncio
import contextlib
import datetime
import importlib

import interactions as ipy
from interactions.ext import prefixed_commands as prefixed

import common.models as models
import common.utils as utils

PREMIUM_REMOVE_MESSAGE = """
Hello! This bot filters out people who do not have a Realms Playerlist Premium \
code but have the Premium Supporter role. It seems like you were caught in the crossfire, so I'd like to address it:

- Did you not have Premium or unsubscribed from it recently? Fair enough, just ignore this message.
- Did you mean to actually get your code and used Ko-Fi? Please follow this Ko-Fi guide on how to re-get it: \
https://help.ko-fi.com/hc/en-us/articles/8664701197073-How-Do-I-Join-a-Creator-s-Discord-Server-#my-role-appears-on-the-creator-s-page-but-is-not-assigned--0-2 - \
from there, make sure to go to <#1029164782617632768> and open a ticket, as *you will not get the code otherwise.*
  - If you used Stripe, you should have gotten the code when you purchased Premium. If you somehow didn't, please email discord@astrea.cc or DM astreatss on Discord right away.
- Want to cancel your subscription? If you use Ko-Fi, they has a guide for that here: https://help.ko-fi.com/hc/en-us/articles/360007556993-How-Do-I-Cancel-a-Subscription-to-a-Creator- - \
otherwise, you can do it through the Realms Playerlist Premium dashboard: https://rpldash.astrea.cc/premium/.
- Using Ko-Fi and want to use a different method to get Premium? A new, simplified version of getting Premium is now in use: \
- *cancel your Premium as above*, but then follow the steps as seen here: https://rpl.astrea.cc/wiki/premium.html
""".strip()


class RealmsPremiumWatch(utils.Extension):
    def __init__(self, bot: utils.SLBotBase):
        self.name = "Realms Playerlist Premium Watch"
        self.bot: utils.SLBotBase = bot
        self.premium_role: ipy.Role = None  # type: ignore
        self.supporter_role: ipy.Role = None  # type: ignore

        asyncio.create_task(self.async_run())

    async def async_run(self):
        await self.bot.fully_ready.wait()
        self.premium_role = await self.bot.guild.fetch_role(1007868499772846081)  # type: ignore
        self.supporter_role = await self.bot.guild.fetch_role(987447832715857961)  # type: ignore
        self.update_roles.start()

    def drop(self) -> None:
        self.update_roles.stop()
        return super().drop()

    @ipy.Task.create(ipy.IntervalTrigger(hours=12))
    async def update_roles(self):
        filter_time = ipy.Timestamp.utcnow() - datetime.timedelta(days=3)

        self.premium_role: ipy.Role = await self.bot.guild.fetch_role(1007868499772846081)  # type: ignore

        values = await models.PremiumCode.all().values("user_id")
        synced_member_ids: set[int] = {
            int(value["user_id"]) for value in values if value["user_id"] is not None
        }

        for member in self.premium_role.members:
            if member.id not in synced_member_ids and member.joined_at < filter_time:
                await member.remove_role(self.premium_role)
                # with contextlib.suppress(ipy.errors.HTTPException):
                #     await member.send(PREMIUM_REMOVE_MESSAGE)

    @ipy.listen()
    async def on_member_update(self, event: ipy.events.MemberUpdate):
        if not self.premium_role:
            return

        if event.before._role_ids == event.after._role_ids:
            return

        if event.before.has_role(self.premium_role) and not event.after.has_role(
            self.premium_role
        ):
            code = await models.PremiumCode.get_or_none(
                user_id=int(event.before.id),
                customer_id__isnull=True,
            ).prefetch_related("guilds")
            if code:
                for config in code.guilds:
                    config.premium_code = None
                    config.live_playerlist = False
                    config.fetch_devices = False
                    config.live_online_channel = None
                    await config.save()
                await code.delete()

    @ipy.listen()
    async def on_member_add(self, event: ipy.events.MemberAdd):
        if not self.premium_role:
            return

        if await models.PremiumCode.exists(
            user_id=int(event.member.id),
            customer_id__not_isnull=True,
        ):
            await event.member.add_roles((self.premium_role, self.supporter_role))

    @ipy.listen()
    async def on_member_remove(self, event: ipy.events.MemberRemove):
        if not self.premium_role:
            return

        if not isinstance(event.member, ipy.Member) or event.member.has_role(
            self.premium_role
        ):
            code = await models.PremiumCode.get_or_none(
                user_id=int(event.member.id),
                customer_id__isnull=True,
            ).prefetch_related("guilds")
            if code:
                for config in code.guilds:
                    config.premium_code = None
                    config.live_playerlist = False
                    config.fetch_devices = False
                    config.live_online_channel = None
                    await config.save()
                await code.delete()

    @prefixed.prefixed_command(aliases=["resync-premium"])
    @ipy.check(ipy.is_owner())
    async def resync_premium(self, ctx: prefixed.PrefixedContext):
        if not self.premium_role:
            return

        async with ctx.channel.typing:
            self.premium_role: ipy.Role = await self.bot.guild.fetch_role(1007868499772846081)  # type: ignore
            member_ids = [member.id for member in self.premium_role.members]
            member_ids.append(self.bot.owner.id)

            async for code in models.PremiumCode.filter(
                user_id__not_in=member_ids,
                customer_id__isnull=True,
            ).prefetch_related("guilds"):
                if code.user_id is None:
                    continue

                for config in code.guilds:
                    config.premium_code = None
                    config.live_playerlist = False
                    config.fetch_devices = False
                    config.live_online_channel = None
                    await config.save()
                await code.delete()

        await ctx.reply("Done!")


def setup(bot):
    importlib.reload(utils)
    RealmsPremiumWatch(bot)
