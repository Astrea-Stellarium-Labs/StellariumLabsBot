import datetime
import importlib

import humanize
import interactions as ipy
from interactions.ext import prefixed_commands as prefixed

import common.utils as utils


class OnCMDError(ipy.Extension):
    def __init__(self, bot: utils.SLBotBase) -> None:
        self.bot: utils.SLBotBase = bot

    @ipy.listen(disable_default_listeners=True)
    async def on_command_error(
        self,
        event: ipy.events.CommandError,
    ) -> None:
        if not isinstance(event.ctx, prefixed.PrefixedContext | ipy.InteractionContext):
            return await utils.error_handle(self.bot, event.error)

        if isinstance(event.error, ipy.errors.CommandOnCooldown):
            delta_wait = datetime.timedelta(
                seconds=event.error.cooldown.get_cooldown_time()
            )
            await event.ctx.send(
                embeds=utils.error_embed_generate(
                    "You're doing that command too fast! " + "Try again in"
                    f" `{humanize.precisedelta(delta_wait, format='%0.0f')}`."
                )
            )
        elif isinstance(event.error, utils.CustomCheckFailure | ipy.errors.BadArgument):
            await event.ctx.send(embeds=utils.error_embed_generate(str(event.error)))
        elif isinstance(event.error, ipy.errors.CommandCheckFailure):
            if event.ctx.guild:
                await event.ctx.send(
                    embeds=utils.error_embed_generate(
                        "You do not have the proper permissions to use that command."
                    )
                )
        else:
            await utils.error_handle(self.bot, event.error, ctx=event.ctx)


def setup(bot: utils.SLBotBase) -> None:
    importlib.reload(utils)
    OnCMDError(bot)
