import importlib

import interactions as ipy
import interactions.ext.prefixed_commands as prefixed

import common.utils as utils


class SelfRoles(utils.Extension):
    def __init__(self, bot):
        self.bot: utils.SLBotBase = bot
        self.name = "Self Roles"

        self.pronoun_roles = {
            "She/Her": 993731445308805180,
            "It/Its": 993731485959995462,
            "He/Him": 993731511335538719,
            "They/Them": 993731574157803661,
            "Neopronouns": 993731619666022402,
            "Any Prnouns": 993731664322764892,
            "Ask for Pronouns": 993731692667863060,
        }

        self.pronoun_select = ipy.StringSelectMenu(
            *(
                ipy.StringSelectOption(label=k, value=f"pronoun:{v}|{k}")
                for k, v in self.pronoun_roles.items()
            ),
            custom_id="pronounselect",
            placeholder="Select your pronouns!",
            min_values=0,
            max_values=len(self.pronoun_roles),
        )

        self.other_roles_components = [
            ipy.Button(
                style=ipy.ButtonStyle.GRAY,
                label="Realms Playerlist News Ping",
                emoji="⛏",
                custom_id="rolebutton|993730531831320586",
            ),
            ipy.Button(
                style=ipy.ButtonStyle.GRAY,
                label="GitHub Log Viewer",
                emoji="📃",
                custom_id="rolebutton|1131832642476724255",
            ),
        ]

        self.verification_button = ipy.Button(
            style=ipy.ButtonStyle.GREEN,
            label="Verify",
            emoji="✅",
            custom_id="rolebutton|775914041440337940",
        )

        self.verify_channel = ipy.GuildText(
            client=self.bot, id=1132483624726429696, type=ipy.ChannelType.GUILD_TEXT  # type: ignore
        )

    @prefixed.prefixed_command()
    @utils.proper_permissions()
    async def send_pronoun_select(self, ctx: prefixed.PrefixedContext):
        embed = ipy.Embed(
            title="Pronouns",
            description=(
                "Select the pronouns you wish to have. They will appear in your profile"
                " as a bright green role.\nAny old pronouns not re-selected will be"
                " removed."
            ),
            color=self.bot.color,
        )

        await ctx.send(embed=embed, components=self.pronoun_select)
        await ctx.message.delete()

    @prefixed.prefixed_command()
    @utils.proper_permissions()
    async def send_other_roles(self, ctx: prefixed.PrefixedContext):
        embed = ipy.Embed(
            title="Other Roles",
            description="Select any other roles you wish to have.",
            color=self.bot.color,
        )

        await ctx.send(embed=embed, components=self.other_roles_components)
        await ctx.message.delete()

    @prefixed.prefixed_command()
    @utils.proper_permissions()
    async def send_verification(self, ctx: prefixed.PrefixedContext):
        embed = ipy.Embed(
            title="Verification",
            description=(
                "Click the button below to verify yourself. This will give you access"
                " to the rest of the server."
            ),
            color=self.bot.color,
        )

        await ctx.send(embed=embed, components=self.verification_button)
        await ctx.message.delete()

    @staticmethod
    async def process_select(
        ctx: ipy.ComponentContext,
        *,
        roles: dict[str, int],
        prefix: str,
        add_text: str,
        remove_text: str,
    ):
        member = ctx.author

        if not isinstance(member, ipy.Member):
            await ctx.send("An error occured. Please try again.", ephemeral=True)
            return

        # do this weirdness since doing member.roles has a cache
        # search cost which can be expensive if there are tons of roles
        member_roles = {int(r) for r in member._role_ids}
        member_roles.difference_update(roles.values())

        if ctx.values:
            add_list = []

            for value in ctx.values:
                value: str
                split_string = value.removeprefix(f"{prefix}:").split("|")
                role = int(split_string[0])
                name = split_string[1]

                member_roles.add(role)
                add_list.append(f"`{name}`")

            await member.edit(roles=list(member_roles))
            await ctx.send(f"New {add_text}: {', '.join(add_list)}.", ephemeral=True)

        else:
            await member.edit(roles=list(member_roles))
            await ctx.send(f"{remove_text} removed.", ephemeral=True)

    @ipy.component_callback("pronounselect")
    async def component_handle(self, ctx: ipy.ComponentContext):
        await self.process_select(
            ctx,
            roles=self.pronoun_roles,
            prefix="pronoun",
            add_text="pronouns",
            remove_text="All pronouns",
        )

    @ipy.listen(ipy.events.ButtonPressed)
    async def button_handle(self, event: ipy.events.ButtonPressed):
        ctx = event.ctx

        if ctx.custom_id.startswith("rolebutton|"):
            member = ctx.author
            if not isinstance(member, ipy.Member):
                await ctx.send("An error occured. Please try again.", ephemeral=True)
                return

            role_id = int(ctx.custom_id.removeprefix("rolebutton|"))
            role = await self.bot.guild.fetch_role(role_id)
            if not role:
                await ctx.send("An error occured. Please try again.", ephemeral=True)
                return

            if member.has_role(role):
                await member.remove_role(role)
                await ctx.send(f"Removed {role.mention}.", ephemeral=True)
            else:
                await member.add_role(role)
                await ctx.send(f"Added {role.mention}.", ephemeral=True)

    @ipy.listen(ipy.events.MemberAdd)
    async def quick_ping(self, event: ipy.events.MemberAdd):
        await self.verify_channel.send(event.member.mention, delete_after=0.2)


def setup(bot):
    importlib.reload(utils)
    SelfRoles(bot)
