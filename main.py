import asyncio
import contextlib
import logging
import os
import typing

import naff
import redis.asyncio as aioredis
from dotenv import load_dotenv
from tortoise import Tortoise

import common.utils as utils

load_dotenv()


logger = logging.getLogger("agbot")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ.get("LOG_FILE_PATH"), encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


async def generate_prefixes(bot: naff.Client, msg: naff.Message):
    # here for future-proofing
    mention_prefixes = {f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "}
    custom_prefixes = {"g!"}
    return mention_prefixes.union(custom_prefixes)


class AGBot(utils.AGBotBase):
    @naff.listen("startup")
    async def on_startup(self):
        self.guild = self.get_guild(775912554928144384)  # type: ignore
        self.fully_ready.set()

    @naff.listen("ready")
    async def on_ready(self):
        utcnow = naff.Timestamp.utcnow()
        time_format = f"<t:{int(utcnow.timestamp())}:f>"

        connect_msg = (
            f"Logged in at {time_format}!"
            if self.init_load == True
            else f"Reconnected at {time_format}!"
        )

        await self.owner.send(connect_msg)

        self.init_load = False

        activity = naff.Activity.create(
            name="over Astrea's Galaxy", type=naff.ActivityType.WATCHING
        )

        await self.change_presence(activity=activity)

    @naff.listen("disconnect")
    async def on_disconnect(self):
        # basically, this needs to be done as otherwise, when the bot reconnects,
        # redis may complain that a connection was closed by a peer
        # this isnt a great solution, but it should work
        with contextlib.suppress(Exception):
            await self.redis.connection_pool.disconnect(inuse_connections=True)

    @naff.listen("resume")
    async def on_resume(self):
        activity = naff.Activity.create(
            name="over Astrea's Galaxy", type=naff.ActivityType.WATCHING
        )
        await self.change_presence(activity=activity)

    @naff.listen("message_create")
    async def _dispatch_prefixed_commands(
        self, event: naff.events.MessageCreate
    ) -> None:
        """Determine if a command is being triggered, and dispatch it.
        Annoyingly, unlike d.py, we have to overwrite this whole method
        in order to provide the 'replace _ with -' trick that was in the
        d.py version."""
        message = event.message

        if not message.content:
            return

        if not message.author.bot:
            prefixes: str | typing.Iterable[str] = await self.generate_prefixes(
                self, message
            )  # type: ingore

            if isinstance(prefixes, str) or prefixes == naff.MENTION_PREFIX:
                prefixes = (prefixes,)  # type: ignore

            prefix_used = None

            for prefix in prefixes:
                if prefix == naff.MENTION_PREFIX:
                    if mention := self._mention_reg.search(message.content):  # type: ignore
                        prefix = mention.group()
                    else:
                        continue

                if message.content.startswith(prefix):
                    prefix_used = prefix
                    break

            if prefix_used:
                context = await self.get_context(message)
                context.prefix = prefix_used

                content_parameters = message.content.removeprefix(prefix_used)  # type: ignore
                command = self  # yes, this is a hack

                while True:
                    first_word: str = naff.utils.get_first_word(content_parameters)  # type: ignore
                    command_first_word: str = (
                        first_word.replace("-", "_") if first_word else first_word
                    )
                    if isinstance(command, naff.PrefixedCommand):
                        new_command = command.subcommands.get(command_first_word)
                    else:
                        new_command = command.prefixed_commands.get(command_first_word)
                    if not new_command or not new_command.enabled:
                        break

                    command = new_command
                    content_parameters = content_parameters.removeprefix(
                        first_word
                    ).strip()

                    if command.subcommands and command.hierarchical_checking:
                        try:
                            await new_command._can_run(
                                context
                            )  # will error out if we can't run this command
                        except Exception as e:
                            if new_command.error_callback:
                                await new_command.error_callback(e, context)
                            elif (
                                new_command.extension
                                and new_command.extension.extension_error
                            ):
                                await new_command.extension.extension_error(context)
                            else:
                                await self.on_command_error(context, e)
                            return

                if not isinstance(command, naff.PrefixedCommand):
                    command = None

                if command and command.enabled:
                    # yeah, this looks ugly
                    context.command = command
                    context.invoke_target = (
                        message.content.removeprefix(prefix_used).removesuffix(content_parameters).strip()  # type: ignore
                    )
                    context.args = naff.utils.get_args(context.content_parameters)
                    try:
                        if self.pre_run_callback:
                            await self.pre_run_callback(context)
                        await self._run_prefixed_command(command, context)
                        if self.post_run_callback:
                            await self.post_run_callback(context)
                    except Exception as e:
                        await self.on_command_error(context, e)
                    finally:
                        await self.on_command(context)

    async def on_error(self, source: str, error: Exception, *args, **kwargs) -> None:
        await utils.error_handle(self, error)

    async def stop(self) -> None:
        await Tortoise.close_connections()  # this will complain a bit, just ignore it
        return await super().stop()


intents = naff.Intents.ALL
mentions = naff.AllowedMentions.all()

bot = AGBot(
    generate_prefixes=generate_prefixes,
    allowed_mentions=mentions,
    intents=intents,
    delete_unused_application_cmds=True,
    fetch_members=True,
    logger=logger,
)
bot.init_load = True
bot.color = naff.Color(int(os.environ.get("BOT_COLOR")))  # 2ebae1, aka 3062497

with contextlib.suppress(ImportError):
    import uvloop

    uvloop.install()


async def start():
    await Tortoise.init(
        db_url=os.environ.get("DB_URL"), modules={"models": ["common.models"]}
    )
    bot.redis = aioredis.from_url(os.environ.get("REDIS_URL"), decode_responses=True)
    bot.fully_ready = asyncio.Event()

    ext_list = utils.get_all_extensions(os.environ.get("DIRECTORY_OF_FILE"))
    for ext in ext_list:
        try:
            bot.load_extension(ext)
        except naff.errors.ExtensionLoadException:
            raise

    await bot.astart(os.environ.get("MAIN_TOKEN"))


asyncio.run(start())
