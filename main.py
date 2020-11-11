from discord.ext import commands
import discord, traceback, os
from datetime import datetime

from keep_alive import keep_alive

def error_format(error):
    # simple function that formats an exception
    return ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))

def string_split(string):
    # simple function that splits a string into 1950-character parts
    return [string[i:i+1950] for i in range(0, len(string), 1950)]

async def proper_permissions(ctx):
    # checks if author has admin or manage guild perms or is the owner
    permissions = ctx.author.guild_permissions
    return (permissions.administrator or permissions.manage_guild
    or ctx.guild.owner.id == ctx.author.id)

async def error_handle(bot, error, ctx = None):
    # handles errors and sends them to owner
    error_str = error_format(error)

    await msg_to_owner(bot, error_str)

    if ctx != None:
        await ctx.send("An internal error has occured. The bot owner has been notified.")

async def msg_to_owner(bot, content):
    # sends a message to the owner
    owner = bot.owner
    string = str(content)

    str_chunks = string_split(string)

    for chunk in str_chunks:
        await owner.send(f"{chunk}")


# we're going to use all intents for laziness purposes
# we could reasonably turn some of these off, but this bot is too small to really matter much
bot = commands.Bot(command_prefix='sp!', fetch_offline_members=True, intents=discord.Intents.all())
bot.remove_command("help")

@bot.event
async def on_ready():
    if bot.init_load == True:
        cogs_list = ("cogs.eval_cmd", "cogs.on_member_update")
        for cog in cogs_list:
            bot.load_extension(cog)

        print('Logged in as')
        print(bot.user.name)
        print(bot.user.id)
        print('------\n')

        activity = discord.Activity(name = 'over Sonic49\'s Bot Support', type = discord.ActivityType.watching)
        await bot.change_presence(activity = activity)

        guild = bot.get_guild(775912554928144384)
        bot.sonic_bot_role = guild.get_role(775913721092374528)

        application = await bot.application_info()
        bot.owner = application.owner

    utcnow = datetime.utcnow()
    time_format = utcnow.strftime("%x %X UTC")

    connect_str = "Connected" if bot.init_load else "Reconnected"

    await msg_to_owner(bot, f"{connect_str} at `{time_format}`!")

    bot.init_load = False

@bot.check
async def block_dms(ctx):
    return ctx.guild is not None

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandInvokeError):
        original = error.original
        if not isinstance(original, discord.HTTPException):
            await error_handle(bot, error, ctx)
    elif isinstance(error, (commands.ConversionError, commands.UserInputError, commands.CommandOnCooldown)):
        await ctx.send(error)
    elif isinstance(error, commands.CheckFailure):
        if ctx.guild != None:
            await ctx.send("You do not have the proper permissions to use that command.")
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        await error_handle(bot, error, ctx)

@bot.event
async def on_error(event, *args, **kwargs):
    try:
        raise
    except Exception as e:
        await error_handle(bot, e)

keep_alive()
bot.init_load = True
bot.run(os.environ.get("MAIN_TOKEN"))