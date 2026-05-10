import asyncio
import contextlib
import logging
import os
import typing
from pathlib import Path

import interactions as ipy
import redis.asyncio as aioredis
from dotenv import load_dotenv
from interactions.ext import prefixed_commands as prefixed
from tortoise import Tortoise

import common.utils as utils

load_dotenv()


file_location = Path(__file__).parent.absolute().as_posix()
os.environ["DIRECTORY_OF_FILE"] = file_location
os.environ["LOG_FILE_PATH"] = f"{file_location}/discord.log"


logger = logging.getLogger("slbot")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ["LOG_FILE_PATH"], encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


class SLBot(utils.SLBotBase):
    @ipy.listen("startup")
    async def on_startup(self) -> None:
        self.guild = self.get_guild(775912554928144384)  # type: ignore
        self.fully_ready.set()

    @ipy.listen("ready")
    async def on_ready(self) -> None:
        utcnow = ipy.Timestamp.utcnow()
        time_format = f"<t:{int(utcnow.timestamp())}:f>"

        connect_msg = (
            f"Logged in at {time_format}!"
            if self.init_load
            else f"Reconnected at {time_format}!"
        )

        await self.owner.send(connect_msg)

        self.init_load = False

        activity = ipy.Activity.create(
            name="over Stellarium Labs", type=ipy.ActivityType.WATCHING
        )

        await self.change_presence(activity=activity)

    @ipy.listen("disconnect")
    async def on_disconnect(self) -> None:
        # basically, this needs to be done as otherwise, when the bot reconnects,
        # redis may complain that a connection was closed by a peer
        # this isnt a great solution, but it should work
        with contextlib.suppress(Exception):
            await self.redis.connection_pool.disconnect(inuse_connections=True)

    @ipy.listen("resume")
    async def on_resume(self) -> None:
        activity = ipy.Activity.create(
            name="over Stellarium Labs", type=ipy.ActivityType.WATCHING
        )
        await self.change_presence(activity=activity)

    @ipy.listen(is_default_listener=True)
    async def on_error(self, event: ipy.events.Error) -> None:
        await utils.error_handle(self, event.error, event.ctx)

    def create_task(self, coro: typing.Coroutine) -> asyncio.Task:
        # see the "important" note below for why we do this (to prevent early gc)
        # https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
        task = asyncio.create_task(coro)
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)
        return task

    async def stop(self) -> None:
        await Tortoise.close_connections()  # this will complain a bit, just ignore it
        await self.redis.aclose()
        return await super().stop()


intents = ipy.Intents.ALL
mentions = ipy.AllowedMentions.all()

bot = SLBot(
    allowed_mentions=mentions,
    intents=intents,
    sync_interactions=False,
    sync_ext=False,
    fetch_members=True,
    disable_dm_commands=True,
    debug_scope=775912554928144384,
    logger=logger,
)
bot.background_tasks = set()
bot.init_load = True
bot.color = ipy.Color(int(os.environ["BOT_COLOR"]))  # 2ebae1, aka 3062497
prefixed.setup(bot, generate_prefixes=prefixed.when_mentioned_or("g!"))


with contextlib.suppress(ImportError):
    import uvloop

    uvloop.install()


async def start() -> None:
    await Tortoise.init(
        db_url=os.environ.get("DB_URL"), modules={"models": ["common.models"]}
    )
    bot.redis = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    bot.fully_ready = asyncio.Event()

    ext_list = utils.get_all_extensions(os.environ["DIRECTORY_OF_FILE"])
    for ext in ext_list:
        try:
            bot.load_extension(ext)
        except ipy.errors.ExtensionLoadException:
            raise

    await bot.astart(os.environ["MAIN_TOKEN"])


asyncio.run(start())
