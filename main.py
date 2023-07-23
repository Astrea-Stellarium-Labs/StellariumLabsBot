import asyncio
import contextlib
import logging
import os

import interactions as ipy
import redis.asyncio as aioredis
from dotenv import load_dotenv
from interactions.ext import prefixed_commands as prefixed
from tortoise import Tortoise

import common.utils as utils

load_dotenv()


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
    async def on_startup(self):
        self.guild = self.get_guild(775912554928144384)  # type: ignore
        self.fully_ready.set()

    @ipy.listen("ready")
    async def on_ready(self):
        utcnow = ipy.Timestamp.utcnow()
        time_format = f"<t:{int(utcnow.timestamp())}:f>"

        connect_msg = (
            f"Logged in at {time_format}!"
            if self.init_load == True
            else f"Reconnected at {time_format}!"
        )

        await self.owner.send(connect_msg)

        self.init_load = False

        activity = ipy.Activity.create(
            name="over Stellarium Labs", type=ipy.ActivityType.WATCHING
        )

        await self.change_presence(activity=activity)

    @ipy.listen("disconnect")
    async def on_disconnect(self):
        # basically, this needs to be done as otherwise, when the bot reconnects,
        # redis may complain that a connection was closed by a peer
        # this isnt a great solution, but it should work
        with contextlib.suppress(Exception):
            await self.redis.connection_pool.disconnect(inuse_connections=True)

    @ipy.listen("resume")
    async def on_resume(self):
        activity = ipy.Activity.create(
            name="over Stellarium Labs", type=ipy.ActivityType.WATCHING
        )
        await self.change_presence(activity=activity)

    async def on_error(self, source: str, error: Exception, *args, **kwargs) -> None:
        await utils.error_handle(self, error)

    async def stop(self) -> None:
        await Tortoise.close_connections()  # this will complain a bit, just ignore it
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
bot.init_load = True
bot.color = ipy.Color(int(os.environ["BOT_COLOR"]))  # 2ebae1, aka 3062497
prefixed.setup(bot, generate_prefixes=prefixed.when_mentioned_or("g!"))


with contextlib.suppress(ImportError):
    import uvloop

    uvloop.install()


async def start():
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
