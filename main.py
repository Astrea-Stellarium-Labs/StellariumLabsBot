import asyncio
import logging
import os
from collections import defaultdict

import dis_snek
import molter
from dotenv import load_dotenv

import common.utils as utils

load_dotenv()


logger = logging.getLogger("dis.snek")
logger.setLevel(logging.INFO)
handler = logging.FileHandler(
    filename=os.environ.get("LOG_FILE_PATH"), encoding="utf-8", mode="a"
)
handler.setFormatter(
    logging.Formatter("%(asctime)s:%(levelname)s:%(name)s: %(message)s")
)
logger.addHandler(handler)


async def generate_prefixes(bot: dis_snek.Snake, msg: dis_snek.Message):
    # here for future-proofing
    mention_prefixes = {f"<@{bot.user.id}> ", f"<@!{bot.user.id}> "}
    custom_prefixes = {"g!"}
    return mention_prefixes.union(custom_prefixes)


class AstreasGalaxyBot(molter.MolterSnake):
    @dis_snek.listen("ready")
    async def on_ready(self):
        utcnow = dis_snek.Timestamp.utcnow()
        time_format = f"<t:{int(utcnow.timestamp())}:f>"

        connect_msg = (
            f"Logged in at {time_format}!"
            if self.init_load == True
            else f"Reconnected at {time_format}!"
        )

        await self.owner.send(connect_msg)

        self.init_load = False

        activity = dis_snek.Activity.create(
            name="over Astrea's Galaxy", type=dis_snek.ActivityType.WATCHING
        )

        await self.change_presence(activity=activity)

    @dis_snek.listen("resume")
    async def on_resume(self):
        activity = dis_snek.Activity.create(
            name="over Astrea's Galaxy", type=dis_snek.ActivityType.WATCHING
        )
        await self.change_presence(activity=activity)

    @dis_snek.listen("message_create")
    async def _dispatch_msg_commands(self, event: dis_snek.events.MessageCreate):
        """Determine if a command is being triggered, and dispatch it.
        Annoyingly, unlike d.py, we have to overwrite this whole method
        in order to provide the 'replace _ with -' trick that was in the
        d.py version."""

        message = event.message

        if not message.content:
            return

        if not message.author.bot:
            prefixes = await self.generate_prefixes(self, message)

            if isinstance(prefixes, str) or prefixes == dis_snek.MENTION_PREFIX:
                prefixes = (prefixes,)  # type: ignore

            prefix_used = None

            for prefix in prefixes:
                if prefix == dis_snek.MENTION_PREFIX:
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
                command = self

                while True:
                    first_word: str = get_first_word(content_parameters)  # type: ignore
                    actual_first_word = (
                        first_word.replace("-", "_") if first_word else None
                    )

                    if isinstance(command, molter.MolterCommand):
                        new_command = command.command_dict.get(actual_first_word)
                    else:
                        new_command = command.commands.get(actual_first_word)
                    if not new_command or not new_command.enabled:
                        break

                    command = new_command
                    content_parameters = content_parameters.removeprefix(
                        first_word
                    ).strip()
                    if not isinstance(command, molter.MolterCommand):
                        # normal message commands can't have subcommands
                        break

                    if command.command_dict and command.hierarchical_checking:
                        await new_command._can_run(context)

                if isinstance(command, dis_snek.Snake):
                    command = None

                if command and command.enabled:
                    # yeah, this looks ugly
                    context.command = command
                    context.invoked_name = (
                        message.content.removeprefix(prefix_used).removesuffix(content_parameters).strip()  # type: ignore
                    )
                    context.args = dis_snek.utils.get_args(context.content_parameters)
                    try:
                        if self.pre_run_callback:
                            await self.pre_run_callback(context)
                        await self._run_message_command(command, context)
                        if self.post_run_callback:
                            await self.post_run_callback(context)
                    except Exception as e:
                        await self.on_command_error(context, e)
                    finally:
                        await self.on_command(context)

    async def on_error(self, source: str, error: Exception, *args, **kwargs) -> None:
        await utils.error_handle(self, error)


intents = dis_snek.Intents.ALL
mentions = dis_snek.AllowedMentions.all()

bot = AstreasGalaxyBot(
    generate_prefixes=generate_prefixes,
    allowed_mentions=mentions,
    intents=intents,
    auto_defer=dis_snek.AutoDefer(enabled=False),  # we already handle deferring
)
bot.init_load = True
bot.color = dis_snek.Color(int(os.environ.get("BOT_COLOR")))  # 10129639, aka #9a90e7

cogs_list = utils.get_all_extensions(os.environ.get("DIRECTORY_OF_FILE"))
for cog in cogs_list:
    try:
        bot.load_extension(cog)
    except dis_snek.errors.ExtensionLoadException:
        raise

asyncio.run(bot.astart(os.environ.get("MAIN_TOKEN")))
