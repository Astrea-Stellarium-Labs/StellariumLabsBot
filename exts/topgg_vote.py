import asyncio
import importlib
import os
import typing

import attrs
import interactions as ipy
import orjson
from aiohttp import web

import common.utils as utils


@attrs.define(kw_only=True)
class BotVote:
    bot: int
    user: int
    type: typing.Literal["upvote", "test"]
    is_weekend: bool = False
    query: str | None = None

    @classmethod
    def from_topgg(cls, data: dict):
        return cls(
            bot=data["bot"],
            user=data["user"],
            type=data["type"],
            is_weekend=data.get("isWeekend", False),
            query=data.get("query"),
        )


class TopGGHandling(ipy.Extension):
    def __init__(self, bot: utils.AGBotBase):
        self.name = "Top.gg Handling"
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

        vote_data = BotVote.from_topgg(await request.json(loads=orjson.loads))

        username: str = f"<@{vote_data.user}>"
        got_role: bool = False

        member = await self.bot.guild.fetch_member(vote_data.user)
        if member:
            if not member.has_role(self.bot_vote_role):
                await member.add_role(self.bot_vote_role)
                got_role = True
        else:
            user = await self.bot.fetch_user(vote_data.user)
            if user:
                username = f"{user.mention} (**{user.tag}**)"

        vote_content = (
            f"{username} has voted for <@{vote_data.bot}> on Top.gg - thank you so"
            " much!"
        )
        if got_role:
            vote_content += (
                f"\n\nThey also got the <@&{self.bot_vote_role}> role for voting for"
                " the first time! Consider voting too if you want a cool role like"
                " that."
            )

        embed = ipy.Embed(
            title="Vote Receieved", description=vote_content, color=self.bot.color
        )
        embed.add_field(
            "Vote for this bot!", f"[Click here!](https://top.gg/bot/{vote_data.bot})"
        )
        content = f"<@{vote_data.user}>" if got_role else None

        await self.bot_vote_channel.send(content=content, embeds=embed)

        return web.Response(status=401)


def setup(bot: utils.AGBotBase) -> None:
    importlib.reload(utils)
    TopGGHandling(bot)
