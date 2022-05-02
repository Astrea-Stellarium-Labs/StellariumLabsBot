import importlib
import typing

import dis_snek

import common.help_paginator as paginator
import common.utils as utils


class HelpCMD(utils.Scale):
    """The cog that handles the help command."""

    def __init__(self, bot: dis_snek.Snake):
        self.display_name = "Help"
        self.bot = bot

    def get_command(self, name: str) -> typing.Optional[dis_snek.PrefixedCommand]:
        """
        Gets a command by the name specified. Can get subcommands of commmands if needed.
        Args:
            name (`str`): The name of the command to search for. Can be its fully qualified name.
        Returns:
            `dis_snek.PrefixedContext`: The command object, if found.
        """
        if " " not in name:
            return self.bot.prefixed_commands.get(name)

        names = name.split()
        if not names:
            return None

        cmd = self.bot.prefixed_commands.get(names[0])
        if not cmd or not isinstance(cmd, dis_snek.PrefixedCommand):
            return cmd

        for name in names[1:]:
            try:
                cmd = cmd.subcommands[name]
            except (AttributeError, KeyError):
                return None

        return cmd

    async def _check_wrapper(
        self, ctx: dis_snek.PrefixedContext, check: typing.Callable
    ) -> bool:
        """A wrapper to ignore errors by checks."""
        try:
            return await check(ctx)
        except Exception:
            return False

    async def _custom_can_run(
        self, ctx: dis_snek.PrefixedContext, cmd: dis_snek.PrefixedCommand
    ):
        """Determines if this command can be run, but ignores cooldowns and concurrency."""
        if not cmd.enabled:
            return False

        for check in cmd.checks:
            if not await self._check_wrapper(ctx, check):
                return False

        if cmd.scale and cmd.scale.scale_checks:
            for check in cmd.scale.scale_checks:
                if not await self._check_wrapper(ctx, check):
                    return False

        return True

    async def get_multi_command_embeds(
        self,
        ctx: dis_snek.PrefixedContext,
        commands: list[dis_snek.PrefixedCommand],
        name: str,
        description: typing.Optional[str],
    ):
        embeds: list[dis_snek.Embed] = []

        command_name_set = {
            c.name for c in commands if await self._custom_can_run(ctx, c)
        }
        commands = [
            c
            for c in commands
            if getattr(c.parent, "name", None) not in command_name_set
        ]
        if not commands:
            return []

        chunks = [commands[x : x + 9] for x in range(0, len(commands), 9)]
        multiple_embeds = len(chunks) > 1

        for index, chunk in enumerate(chunks):
            embed = dis_snek.Embed(description=description, color=ctx.bot.color)

            embed.add_field(
                name="Support",
                value=(
                    "For more help, join the official support server:"
                    " https://discord.gg/NSdetwGjpK"
                ),
                inline=False,
            )
            embed.set_footer(
                text=f'Use "{ctx.prefix}help command" for more info on a command.'
            )

            embed.title = f"{name} - Page {index + 1}" if multiple_embeds else name
            for cmd in chunk:
                signature = f"{cmd.qualified_name.replace('_', '-')} {cmd.signature}"
                embed.add_field(
                    name=signature, value=cmd.brief or "No help given.", inline=False
                )

            embeds.append(embed)

        return embeds

    async def get_scale_cmd_embeds(
        self, ctx: dis_snek.PrefixedContext, scale: dis_snek.Scale
    ):
        msg_cmds = [
            c for c in scale.commands if isinstance(c, dis_snek.PrefixedCommand)
        ]

        if not msg_cmds:
            return []

        name = getattr(scale, "display_name", scale.name) + " Commands"
        return await self.get_multi_command_embeds(
            ctx, msg_cmds, name, scale.description
        )

    async def get_all_cmd_embeds(
        self, ctx: dis_snek.PrefixedContext, bot: dis_snek.Snake
    ):
        embeds: list[dis_snek.Embed] = []

        for scale in bot.scales.values():
            scale_cmd_embeds = await self.get_scale_cmd_embeds(ctx, scale)
            if scale_cmd_embeds:
                embeds.extend(scale_cmd_embeds)

        return embeds

    async def get_command_embeds(
        self, ctx: dis_snek.PrefixedContext, command: dis_snek.PrefixedCommand
    ):
        if not command.parent and not await self._custom_can_run(ctx, command):
            return []

        command_name_fmt = ""
        if command.parent:
            command_name_fmt = f"{command.parent.qualified_name.replace('_', '-')} "

        if command.aliases:
            aliases = "|".join(a.replace("_", "-") for a in command.aliases)
            fmt = f"[{command.name.replace('_', '-')}|{aliases}]"
        else:
            fmt = f"{command.name.replace('_', '-')}"

        command_name_fmt += fmt
        signature = f"{command_name_fmt} {command.signature}"

        if command.is_subcommand:
            return await self.get_multi_command_embeds(
                ctx, list(command.all_subcommands), signature, command.help
            )
        else:
            return [
                dis_snek.Embed(
                    title=signature, description=command.help, color=ctx.bot.color
                )
            ]

    @dis_snek.prefixed_command()
    @dis_snek.cooldown(dis_snek.Buckets.MEMBER, 1, 3)  # type: ignore
    async def help(self, ctx: dis_snek.PrefixedContext, *, query: typing.Optional[str]):
        """Shows help about the bot, a command, or a category."""
        await ctx.channel.trigger_typing()

        embeds: list[dis_snek.Embed] = []

        if not query:
            embeds = await self.get_all_cmd_embeds(ctx, self.bot)
        else:
            query_fix = query.replace("-", "_")
            if command := self.get_command(query_fix):
                embeds = await self.get_command_embeds(ctx, command)
            else:
                scale: typing.Optional[dis_snek.Scale] = next(
                    (
                        s
                        for s in self.bot.scales.values()
                        if s.name.lower() == query.lower()
                    ),
                    None,
                )
                if not scale:
                    raise dis_snek.errors.BadArgument(
                        f'No command called "{query}" found.'
                    )

                embeds = await self.get_scale_cmd_embeds(ctx, scale)
                if not embeds:
                    raise dis_snek.errors.BadArgument(
                        f"No message commands for {scale.name}."
                    )

        if len(embeds) == 1:
            # pointless to do a paginator here
            await ctx.reply(embeds=embeds)
            return

        pag = paginator.HelpPaginator.create_from_embeds(self.bot, *embeds, timeout=60)
        await pag.send(ctx)


def setup(bot):
    importlib.reload(utils)
    HelpCMD(bot)
