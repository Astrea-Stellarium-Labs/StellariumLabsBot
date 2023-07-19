import asyncio
import datetime
import importlib
import os

import interactions as ipy
import orjson
from aiohttp import web

import common.utils as utils

TWELVE_HOURS = int(datetime.timedelta(hours=12).total_seconds())


class VoteHandling(ipy.Extension):
    def __init__(self, bot: utils.AGBotBase):
        self.name = "Vote Handling"
        self.bot: utils.AGBotBase = bot
        self.bot_vote_channel: ipy.GuildText = None  # type: ignore
        self.runner: web.AppRunner = None  # type: ignore
        self.bot_vote_role: int = 1122748827649192027

        asyncio.create_task(self.fill_topgg_info())

    def drop(self) -> None:
        asyncio.create_task(self.runner.cleanup())
        return super().drop()

    async def fill_topgg_info(self):
        await self.bot.fully_ready.wait()
        self.bot_vote_channel = await self.bot.fetch_channel(1122755262466498590)  # type: ignore

        app = web.Application()
        app.add_routes([web.post("/topgg", self.topgg_handling)])
        app.add_routes([web.post("/dbl_rpl", self.dbl_handling)])
        app.add_routes([web.post("/discordscom", self.discords_com_handler)])
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 8000)
        await site.start()

    async def topgg_handling(
        self,
        request: web.Request,
    ):
        authorization = request.headers.get("Authorization")
        if not authorization or authorization != os.environ["TOPGG_AUTH"]:
            return web.Response(status=401)

        vote_data = await request.json(loads=orjson.loads)
        user_id = int(vote_data["user"])
        bot_id = int(vote_data["bot"])

        if bot_id == 725483868777611275 and vote_data["type"] != "test":
            # note: im specifically trying to encourage top.gg only votes
            _ = asyncio.create_task(
                self.bot.redis.setex(f"rpl-voted-{user_id}", TWELVE_HOURS, "1")
            )

        __ = asyncio.create_task(
            self.handle_vote(
                f"<@{user_id}>",
                user_id,
                int(vote_data["bot"]),
                "Top.gg",
                "https://top.gg/bot/{bot_id}",
            )
        )

        return web.Response(status=200)

    async def dbl_handling(self, request: web.Request):
        authorization = request.headers.get("Authorization")
        if not authorization or authorization != os.environ["DBL_AUTH"]:
            return web.Response(status=401)

        vote_data = await request.json(loads=orjson.loads)
        user_id = int(vote_data["id"])
        _ = asyncio.create_task(
            self.handle_vote(
                f"<@{user_id}> (**@{vote_data['username']})**",
                user_id,
                725483868777611275,
                "Discord Bot List",
                "https://discordbotlist.com/bots/realms-playerlist-bot",
            )
        )

        return web.Response(status=200)

    async def discords_com_handler(self, request: web.Request):
        authorization = request.headers.get("Authorization")
        if not authorization or authorization != os.environ["DISCORDSCOM_AUTH"]:
            return web.Response(status=401)

        vote_data = await request.json(loads=orjson.loads)
        user_id = int(vote_data["user"])
        maybe_bot_id = vote_data["bot"]
        bot_id = int(maybe_bot_id) if maybe_bot_id.isdigit() else 725483868777611275

        _ = asyncio.create_task(
            self.handle_vote(
                f"<@{user_id}>",
                user_id,
                bot_id,
                "Discords.com",
                "https://discords.com/bots/bot/{bot_id}",
            )
        )

        return web.Response(status=200)

    async def handle_vote(
        self, username: str, user_id: int, bot_id: int, site_name: str, vote_url: str
    ):
        try:
            got_role: bool = False

            member = await self.bot.guild.fetch_member(user_id)
            if member:
                username = f"{member.mention} (**{member.tag}**)"
                if not member.has_role(self.bot_vote_role):
                    await member.add_role(self.bot_vote_role)
                    got_role = True
            else:
                user = await self.bot.fetch_user(user_id)
                if user:
                    username = f"{user.mention} (**{user.tag}**)"

            vote_content = (
                f"{username} has voted for <@{bot_id}> on **{site_name}** - thank you"
                " so much!"
            )
            if got_role:
                vote_content += (
                    f"\n\nThey also got the <@&{self.bot_vote_role}> role for voting"
                    " for the first time! Consider voting too if you want a cool role"
                    " like that."
                )

            embed = ipy.Embed(
                title="Vote Receieved", description=vote_content, color=self.bot.color
            )
            embed.add_field(
                "Vote for this bot!", f"[Click here!]({vote_url.format(bot_id=bot_id)})"
            )
            content = f"<@{user_id}>" if got_role else None

            await self.bot_vote_channel.send(content=content, embeds=embed)
        except Exception as e:
            await utils.error_handle(self.bot, e)


def setup(bot: utils.AGBotBase) -> None:
    importlib.reload(utils)
    VoteHandling(bot)
