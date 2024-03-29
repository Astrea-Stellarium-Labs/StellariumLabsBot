import typing
from datetime import datetime

from tortoise import fields
from tortoise.models import Model


class GuildConfig(Model):
    class Meta:
        table = "realmguildconfig"

    guild_id: int = fields.BigIntField(pk=True)
    club_id: typing.Optional[str] = fields.CharField(50, null=True)
    playerlist_chan: typing.Optional[int] = fields.BigIntField(null=True)
    realm_id: typing.Optional[str] = fields.CharField(50, null=True)
    live_playerlist: bool = fields.BooleanField(default=False)  # type: ignore
    realm_offline_role: typing.Optional[int] = fields.BigIntField(null=True)
    warning_notifications: bool = fields.BooleanField(default=True)  # type: ignore
    fetch_devices: bool = fields.BooleanField(default=False)  # type: ignore
    live_online_channel: typing.Optional[str] = fields.CharField(75, null=True)  # type: ignore
    premium_code: fields.ForeignKeyNullableRelation[
        "PremiumCode"
    ] = fields.ForeignKeyField(
        "models.PremiumCode",
        related_name="guilds",
        on_delete=fields.SET_NULL,
        null=True,
    )  # type: ignore


class PremiumCode(Model):
    class Meta:
        table = "realmpremiumcode"

    id: int = fields.IntField(pk=True)
    code: str = fields.CharField(100)
    user_id: int | None = fields.BigIntField(null=True)
    uses: int = fields.IntField(default=0)
    max_uses: int = fields.IntField(default=2)
    customer_id: typing.Optional[str] = fields.CharField(50, null=True)
    expires_at: typing.Optional[datetime] = fields.DatetimeField(null=True)

    guilds: fields.ReverseRelation["GuildConfig"]
