import asyncio
import collections
import logging
import traceback
import typing
from pathlib import Path

import aiohttp
import interactions as ipy
import redis.asyncio as aioredis
from interactions.ext import prefixed_commands as prefixed


class CustomCheckFailure(ipy.errors.BadArgument):
    # custom classs for custom prerequisite failures outside of normal command checks
    pass


def proper_permissions():
    async def predicate(ctx: ipy.BaseContext):
        return (
            ipy.Permissions.ADMINISTRATOR in ctx.author.guild_permissions
            or ipy.Permissions.MANAGE_GUILD in ctx.author.guild_permissions
        )

    return ipy.check(predicate)


def permissions_check(ctx: ipy.BaseContext):
    return (
        ipy.Permissions.ADMINISTRATOR in ctx.author.guild_permissions
        or ipy.Permissions.MANAGE_GUILD in ctx.author.guild_permissions
    )


async def error_handle(bot: ipy.Client, error: Exception, ctx: ipy.BaseContext = None):
    # handles errors and sends them to owner
    if isinstance(error, aiohttp.ServerDisconnectedError):
        to_send = "Disconnected from server!"
        split = True
    else:
        error_str = error_format(error)
        logging.getLogger("agbot").error(error_str)

        chunks = line_split(error_str)
        for i in range(len(chunks)):
            chunks[i][0] = f"```py\n{chunks[i][0]}"
            chunks[i][len(chunks[i]) - 1] += "\n```"

        final_chunks = ["\n".join(chunk) for chunk in chunks]
        if ctx and hasattr(ctx, "message") and hasattr(ctx.message, "jump_url"):
            final_chunks.insert(0, f"Error on: {ctx.message.jump_url}")

        to_send = final_chunks
        split = False

    await msg_to_owner(bot, to_send, split)

    if ctx:
        if isinstance(ctx, prefixed.PrefixedContext):
            await ctx.reply(
                "An internal error has occured. The bot owner has been notified."
            )
        elif isinstance(ctx, ipy.InteractionContext):
            await ctx.send(
                content=(
                    "An internal error has occured. The bot owner has been notified."
                )
            )


async def msg_to_owner(bot: ipy.Client, content, split=True):
    # sends a message to the owner
    string = str(content)

    str_chunks = string_split(string) if split else content
    for chunk in str_chunks:
        await bot.owner.send(f"{chunk}")


def line_split(content: str, split_by=20):
    content_split = content.splitlines()
    return [
        content_split[x : x + split_by] for x in range(0, len(content_split), split_by)
    ]


def embed_check(embed: ipy.Embed) -> bool:
    """Checks if an embed is valid, as per Discord's guidelines.
    See https://discord.com/developers/docs/resources/channel#embed-limits for details.
    """
    if len(embed) > 6000:
        return False

    if embed.title and len(embed.title) > 256:
        return False
    if embed.description and len(embed.description) > 4096:
        return False
    if embed.author and embed.author.name and len(embed.author.name) > 256:
        return False
    if embed.footer and embed.footer.text and len(embed.footer.text) > 2048:
        return False
    if embed.fields:
        if len(embed.fields) > 25:
            return False
        for field in embed.fields:
            if field.name and len(field.name) > 1024:
                return False
            if field.value and len(field.value) > 2048:
                return False

    return True


def deny_mentions(user):
    # generates an AllowedMentions object that only pings the user specified
    return ipy.AllowedMentions(users=[user])


def error_format(error: Exception):
    # simple function that formats an exception
    return "".join(
        traceback.format_exception(  # type: ignore
            type(error), value=error, tb=error.__traceback__
        )
    )


def string_split(string):
    # simple function that splits a string into 1950-character parts
    return [string[i : i + 1950] for i in range(0, len(string), 1950)]


def file_to_ext(str_path, base_path):
    # changes a file to an import-like string
    str_path = str_path.replace(base_path, "")
    str_path = str_path.replace("/", ".")
    return str_path.replace(".py", "")


def get_all_extensions(str_path: str, folder="exts"):
    # gets all extensions in a folder
    ext_files = collections.deque()
    loc_split = str_path.split(folder)
    base_path = loc_split[0]

    if base_path == str_path:
        base_path = base_path.replace("main.py", "")
    base_path = base_path.replace("\\", "/")

    if base_path[-1] != "/":
        base_path += "/"

    pathlist = Path(f"{base_path}/{folder}").glob("**/*.py")
    for path in pathlist:
        str_path = str(path.as_posix())
        str_path = file_to_ext(str_path, base_path)

        if str_path != "exts.db_handler":
            ext_files.append(str_path)

    return ext_files


def toggle_friendly_str(bool_to_convert):
    return "on" if bool_to_convert == True else "off"


def yesno_friendly_str(bool_to_convert):
    return "yes" if bool_to_convert == True else "no"


def error_embed_generate(error_msg):
    return ipy.Embed(color=ipy.MaterialColors.RED, description=error_msg)


def generate_mentions(ctx: ipy.BaseContext):
    # generates an AllowedMentions object that is similar to what a user can usually use

    permissions = ctx.channel.permissions_for(ctx.author)
    if (
        ipy.Permissions.ADMINISTRATOR in permissions
        or ipy.Permissions.MENTION_EVERYONE in permissions
    ):
        return ipy.AllowedMentions.all()

    pingable_roles = tuple(r for r in ctx.guild.roles if r.mentionable)
    return ipy.AllowedMentions(parse=["users"], roles=pingable_roles)


def role_check(ctx: ipy.BaseContext, role: ipy.Role):
    top_role = ctx.guild.me.top_role

    if role.position > top_role.position:
        raise CustomCheckFailure(
            "The role provided is a role that is higher than the roles I can edit. "
            + "Please move either that role or my role so that "
            + "my role is higher than the role you want to use."
        )

    return True


async def _global_checks(ctx: ipy.BaseContext):
    if not ctx.bot.is_ready:
        return False

    if ctx.bot.init_load:
        return False

    if not ctx.guild:
        return False

    return True


class Extension(ipy.Extension):
    def __new__(cls, bot: ipy.Client, *args, **kwargs):
        new_cls = super().__new__(cls, bot, *args, **kwargs)
        new_cls.add_ext_check(_global_checks)
        return new_cls


class AGBotBase(prefixed.PrefixedInjectedClient):
    if typing.TYPE_CHECKING:
        init_load: bool
        color: ipy.Color
        owner: ipy.User
        redis: aioredis.Redis
        guild: ipy.Guild
        fully_ready: asyncio.Event
