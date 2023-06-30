import asyncio
import contextlib
import importlib

import interactions as ipy
from interactions.ext import prefixed_commands as prefixed

import common.models as models
import common.utils as utils


class RealmsPremiumWatch(utils.Extension):
    def __init__(self, bot: utils.AGBotBase):
        self.name = "Realms Playerlist Premium Watch"
        self.bot: utils.AGBotBase = bot
        self.premium_role: ipy.Role = None  # type: ignore

        asyncio.create_task(self.async_start())

    async def async_start(self):
        await self.bot.fully_ready.wait()
        self.premium_role = await self.bot.guild.fetch_role(1007868499772846081)  # type: ignore
        self.update_roles.start()

    def drop(self) -> None:
        self.update_roles.stop()
        return super().drop()

    @ipy.Task.create(ipy.IntervalTrigger(hours=6))
    async def update_roles(self):
        self.premium_role: ipy.Role = await self.bot.guild.fetch_role(1007868499772846081)  # type: ignore
        member_ids: list[int] = [int(member.id) for member in self.premium_role.members]  # type: ignore

        values = await models.PremiumCode.filter(user_id__in=member_ids).values(
            "user_id"
        )
        synced_member_ids: set[int] = {int(value["user_id"]) for value in values}

        for member in self.premium_role.members:
            if member.id not in synced_member_ids:
                await member.remove_role(self.premium_role)

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

        elif not event.before.has_role(self.premium_role) and event.after.has_role(
            self.premium_role
        ):
            if not await models.PremiumCode.exists(
                user_id=int(event.before.id),
            ):
                with contextlib.suppress(ipy.errors.HTTPException):
                    await event.after.send(
                        "Hey! Thank you for donating and getting Realms Playerlist"
                        " Premium!\n\nTo get your Premium code, check out"
                        " <#1029164782617632768> and open a ticket. Astrea will be able"
                        " to give your code from there."
                    )

    @ipy.listen()
    async def on_member_add(self, event: ipy.events.MemberAdd):
        if not self.premium_role:
            return

        if await models.PremiumCode.exists(
            user_id=int(event.member.id),
            customer_id__not_isnull=True,
        ):
            await event.member.add_role(self.premium_role)

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
