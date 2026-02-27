"""Pydantic configuration models for Tux.

This module contains all the Pydantic models for configuration,
extracted from the existing config.py file for better organization.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Annotated, Any, cast

from pydantic import BaseModel, Field, field_validator

if TYPE_CHECKING:
    import discord


def _coerce_snowflake_id(v: Any) -> int | None:
    """Coerce TEMPVC ID from int, str, or None to int | None.

    Accepts unquoted integers and quoted strings in JSON, and string env vars.
    """
    if v is None:
        return None
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        s = v.strip()
        return int(s) if s else None
    msg = f"TEMPVC ID must be int, str, or null, got {type(v).__name__}"
    raise ValueError(msg)


class BotInfo(BaseModel):
    """Bot information configuration."""

    BOT_NAME: Annotated[
        str,
        Field(
            default="Tux",
            description="Name of the bot",
            examples=["Tux", "MyBot"],
        ),
    ]
    ACTIVITIES: Annotated[
        list[dict[str, Any]],
        Field(
            default_factory=list,
            description="Bot activities (Playing, Streaming, etc.). Each item: type, name; streaming also needs url.",
            examples=[
                [{"type": "playing", "name": "with Linux"}],
                [
                    {
                        "type": "streaming",
                        "name": "to commands",
                        "url": "https://twitch.tv/example",
                    },
                ],
            ],
        ),
    ]

    @field_validator("ACTIVITIES", mode="before")
    @classmethod
    def validate_activities(cls, v: Any) -> list[dict[str, Any]]:
        """Normalize ACTIVITIES to a list of activity dicts.

        Accepts: JSON string (from env or legacy config), list, or dict (wrapped as
        single-item list). Env vars and string config are parsed as JSON.

        Returns
        -------
        list[dict[str, Any]]
            List of {type, name, url?} activity objects.

        Raises
        ------
        ValueError
            If a string value is not valid JSON or does not decode to a list.
        """
        if v is None:
            return []
        if isinstance(v, list):
            return cast(list[dict[str, Any]], v)
        if isinstance(v, dict):
            return [v]
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            try:
                parsed: Any = json.loads(s)
            except json.JSONDecodeError as e:
                msg = f"ACTIVITIES must be valid JSON: {e}"
                raise ValueError(msg) from e
            if isinstance(parsed, list):
                return cast(list[dict[str, Any]], parsed)
            if isinstance(parsed, dict):
                return [parsed]
            msg = (
                f"ACTIVITIES JSON must be a list or object, got {type(parsed).__name__}"
            )
            raise ValueError(msg)
        msg = (
            f"ACTIVITIES must be a string, list, or dict, got {type(v).__name__}: {v!r}"
        )
        raise ValueError(msg)

    HIDE_BOT_OWNER: Annotated[
        bool,
        Field(
            default=False,
            description="Hide bot owner info",
            examples=[False, True],
        ),
    ]
    PREFIX: Annotated[
        str,
        Field(
            default="$",
            description="Command prefix",
            examples=["$", "!", "tux.", "?"],
        ),
    ]


class UserIds(BaseModel):
    """User ID configuration."""

    BOT_OWNER_ID: Annotated[
        int,
        Field(
            default=0,
            description="Bot owner user ID",
            examples=[123456789012345678],
        ),
    ]
    SYSADMINS: Annotated[
        list[int],
        Field(
            default_factory=list,
            description="System admin user IDs",
            examples=[[123456789012345678, 987654321098765432]],
        ),
    ]


class StatusRoles(BaseModel):
    """Status roles configuration."""

    MAPPINGS: Annotated[
        list[dict[str, Any]],
        Field(
            default_factory=list,
            description="Status to role mappings",
            examples=[[{"status": ".gg/linux", "role_id": 123456789012345678}]],
        ),
    ]


class TempVC(BaseModel):
    """Temporary voice channel configuration.

    IDs accept integer or string in JSON (and string from env); both are coerced to int.
    """

    TEMPVC_CHANNEL_ID: Annotated[
        int | None,
        Field(
            default=None,
            description="Temporary VC channel ID (Join to Create). int or str in JSON.",
            examples=[123456789012345678],
        ),
    ]
    TEMPVC_CATEGORY_ID: Annotated[
        int | None,
        Field(
            default=None,
            description="Temporary VC category ID. int or str in JSON.",
            examples=[123456789012345678],
        ),
    ]

    @field_validator("TEMPVC_CHANNEL_ID", "TEMPVC_CATEGORY_ID", mode="before")
    @classmethod
    def _coerce_tempvc_id(cls, v: Any) -> int | None:
        return _coerce_snowflake_id(v)


class GifLimiter(BaseModel):
    """GIF limiter configuration."""

    RECENT_GIF_AGE: Annotated[
        int,
        Field(
            default=60,
            description="Recent GIF age limit",
            examples=[60, 120, 300],
        ),
    ]
    GIF_LIMITS_USER: Annotated[
        dict[int, int],
        Field(
            default_factory=dict,
            description="User GIF limits",
            examples=[{"123456789012345678": 5}],
        ),
    ]
    GIF_LIMITS_CHANNEL: Annotated[
        dict[int, int],
        Field(
            default_factory=dict,
            description="Channel GIF limits",
            examples=[{"123456789012345678": 10}],
        ),
    ]
    GIF_LIMIT_EXCLUDE: Annotated[
        list[int],
        Field(
            default_factory=list,
            description="Excluded channels",
            examples=[[123456789012345678]],
        ),
    ]


class XP(BaseModel):
    """XP system configuration."""

    XP_BLACKLIST_CHANNELS: Annotated[
        dict[int, list[int]],
        Field(
            default_factory=dict,
            description="XP blacklist channels per server",
            examples=[{123456789012345678: [987654321098765432, 876543210987654321]}],
        ),
    ]
    XP_ROLES: Annotated[
        dict[int, list[dict[str, int]]],
        Field(
            default_factory=dict,
            description="Per server XP roles",
            examples=[
                {
                    123456789012345678: [
                        {"level": 5, "role_id": 987654321098765432},
                        {"level": 10, "role_id": 876543210987654321},
                    ],
                },
            ],
        ),
    ]
    XP_MULTIPLIERS: Annotated[
        dict[int, list[dict[str, int | float]]],
        Field(
            default_factory=dict,
            description="XP multipliers per server",
            examples=[
                {
                    123456789012345678: [
                        {"role_id": 987654321098765432, "multiplier": 1.5},
                        {"role_id": 876543210987654321, "multiplier": 2.0},
                    ],
                },
            ],
        ),
    ]
    XP_COOLDOWN: Annotated[
        dict[int, int],
        Field(
            default_factory=lambda: {0: 1},
            description="XP cooldown in seconds per server (0 for default)",
            examples=[
                {
                    0: 1,  # Default cooldown
                    123456789012345678: 5,  # Server-specific cooldown
                    987654321098765432: 10,
                },
            ],
        ),
    ]
    LEVELS_EXPONENT: Annotated[
        dict[int, float],
        Field(
            default_factory=lambda: {0: 2.0},
            description="Levels exponent per server (0 for default)",
            examples=[
                {
                    0: 2.0,  # Default exponent
                    123456789012345678: 1.5,  # Server-specific exponent
                    987654321098765432: 3.0,
                },
            ],
        ),
    ]
    SHOW_XP_PROGRESS: Annotated[
        dict[int, bool],
        Field(
            default_factory=lambda: {0: True},
            description="Show XP progress per server (0 for default)",
            examples=[
                {
                    0: True,  # Default setting
                    123456789012345678: False,  # Server-specific setting
                },
            ],
        ),
    ]
    ENABLE_XP_CAP: Annotated[
        dict[int, bool],
        Field(
            default_factory=lambda: {0: False},
            description="Enable XP cap per server (0 for default)",
            examples=[
                {
                    0: False,  # Default setting
                    123456789012345678: True,  # Server-specific setting
                },
            ],
        ),
    ]


class Snippets(BaseModel):
    """Snippets configuration."""

    ENABLED: Annotated[
        bool,
        Field(
            default=True,
            description="Enable or disable the snippets module globally",
            examples=[True, False],
        ),
    ]
    LIMIT_TO_ROLE_IDS: Annotated[
        bool,
        Field(
            default=False,
            description="Limit snippets to specific roles",
            examples=[False, True],
        ),
    ]
    ACCESS_ROLE_IDS: Annotated[
        list[int],
        Field(
            default_factory=list,
            description="Snippet access role IDs",
            examples=[[123456789012345678, 987654321098765432]],
        ),
    ]


class IRC(BaseModel):
    """IRC bridge configuration."""

    BRIDGE_WEBHOOK_IDS: Annotated[
        list[int],
        Field(
            default_factory=list,
            description="IRC bridge webhook IDs",
            examples=[[123456789012345678]],
        ),
    ]


class Moderation(BaseModel):
    """Moderation configuration."""

    CROSS_SERVER_GUILD_IDS: Annotated[
        list[int],
        Field(
            default_factory=list,
            description="Guild IDs where moderation actions should be synchronized",
            examples=[[123456789012345678, 987654321098765432]],
        ),
    ]


class VerificationConfig(BaseModel):
    """Per-guild verification configuration."""

    VERIFIED_ROLE_ID: int = Field(
        default=0,
        description="Role ID to give to verified users",
    )
    GROUP_MEMBER_ROLE_ID: int = Field(
        default=0,
        description="Role ID to give to users in the specified Roblox group",
    )
    ROBLOX_GROUP_ID: int = Field(
        default=16185131,
        description="Roblox group ID to check for membership",
    )


class Verification(BaseModel):
    """Verification configuration."""

    GUILDS: Annotated[
        dict[int, VerificationConfig],
        Field(
            default_factory=lambda: {0: VerificationConfig()},
            description="Per-server verification settings (use guild ID 0 for defaults)",
        ),
    ]


class ExternalServices(BaseModel):
    """External services configuration."""

    SENTRY_DSN: Annotated[
        str,
        Field(
            default="",
            description="Sentry DSN",
            examples=["https://key@o123456.ingest.sentry.io/123456"],
        ),
    ]
    SENTRY_ENVIRONMENT: Annotated[
        str,
        Field(
            default="",
            description="Sentry environment (development, production, etc.)",
            examples=["development", "production"],
        ),
    ]
    GITHUB_APP_ID: Annotated[
        str,
        Field(
            default="",
            description="GitHub app ID",
            examples=["123456"],
        ),
    ]
    GITHUB_INSTALLATION_ID: Annotated[
        str,
        Field(
            default="",
            description="GitHub installation ID",
            examples=["12345678"],
        ),
    ]
    GITHUB_PRIVATE_KEY: Annotated[
        str,
        Field(
            default="",
            description="GitHub private key",
            examples=["-----BEGIN RSA PRIVATE KEY-----\n..."],
        ),
    ]
    GITHUB_CLIENT_ID: Annotated[
        str,
        Field(
            default="",
            description="GitHub client ID",
            examples=["Iv1.1234567890abcdef"],
        ),
    ]
    GITHUB_CLIENT_SECRET: Annotated[
        str,
        Field(
            default="",
            description="GitHub client secret",
            examples=["1234567890abcdef1234567890abcdef12345678"],
        ),
    ]
    GITHUB_REPO_URL: Annotated[
        str,
        Field(
            default="",
            description="GitHub repository URL",
            examples=["https://github.com/owner/repo"],
        ),
    ]
    GITHUB_REPO_OWNER: Annotated[
        str,
        Field(
            default="",
            description="GitHub repository owner",
            examples=["owner"],
        ),
    ]
    GITHUB_REPO: Annotated[
        str,
        Field(
            default="",
            description="GitHub repository name",
            examples=["repo"],
        ),
    ]
    MAILCOW_API_KEY: Annotated[
        str,
        Field(
            default="",
            description="Mailcow API key",
            examples=["abc123def456ghi789"],
        ),
    ]
    MAILCOW_API_URL: Annotated[
        str,
        Field(
            default="",
            description="Mailcow API URL",
            examples=["https://mail.example.com/api/v1"],
        ),
    ]
    WOLFRAM_APP_ID: Annotated[
        str,
        Field(
            default="",
            description="Wolfram Alpha app ID",
            examples=["ABC123-DEF456GHI789"],
        ),
    ]
    INFLUXDB_TOKEN: Annotated[
        str,
        Field(
            default="",
            description="InfluxDB token",
            examples=["abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"],
        ),
    ]
    INFLUXDB_URL: Annotated[
        str,
        Field(
            default="",
            description="InfluxDB URL",
            examples=["https://us-east-1-1.aws.cloud2.influxdata.com"],
        ),
    ]
    INFLUXDB_ORG: Annotated[
        str,
        Field(
            default="",
            description="InfluxDB organization",
            examples=["my-org"],
        ),
    ]


class BotIntents(BaseModel):
    """Discord bot gateway intents configuration.

    All three privileged intents are required for full bot functionality:
    - members: Required for on_member_join, on_member_remove, member tracking
    - presences: Required for on_presence_update, status_roles feature
    - message_content: Required for message.content access, prefix commands

    Note: Having both members + presences reduces startup chunking time significantly.
    """

    presences: Annotated[
        bool,
        Field(
            default=True,
            description="Enable presences intent (required for status_roles)",
            examples=[True, False],
        ),
    ]
    members: Annotated[
        bool,
        Field(
            default=True,
            description="Enable members intent (required for jail, tty_roles)",
            examples=[True, False],
        ),
    ]
    message_content: Annotated[
        bool,
        Field(
            default=True,
            description="Enable message content intent (required for most features)",
            examples=[True, False],
        ),
    ]

    def to_discord_intents(self) -> discord.Intents:
        """Convert config to discord.Intents object.

        Returns
        -------
        discord.Intents
            Configured Discord intents object.
        """
        import discord as discord_lib  # noqa: PLC0415

        intents = discord_lib.Intents.default()
        intents.message_content = self.message_content
        intents.presences = self.presences
        intents.members = self.members
        return intents


class DatabaseConfig(BaseModel):
    """Database configuration with automatic URL construction."""

    # Individual database credentials (standard PostgreSQL env vars)
    POSTGRES_HOST: Annotated[
        str,
        Field(
            default="localhost",
            description="PostgreSQL host",
            examples=["localhost", "tux-postgres", "db.example.com"],
        ),
    ]
    POSTGRES_PORT: Annotated[
        int,
        Field(
            default=5432,
            description="PostgreSQL port",
            examples=[5432, 5433],
        ),
    ]
    POSTGRES_DB: Annotated[
        str,
        Field(
            default="tuxdb",
            description="PostgreSQL database name",
            examples=["tuxdb", "tux_production"],
        ),
    ]
    POSTGRES_USER: Annotated[
        str,
        Field(
            default="tuxuser",
            description="PostgreSQL username",
            examples=["tuxuser", "tux_admin"],
        ),
    ]
    POSTGRES_PASSWORD: Annotated[
        str,
        Field(
            default="ChangeThisToAStrongPassword123!",
            description="PostgreSQL password",
            examples=["ChangeThisToAStrongPassword123!", "SecurePassword456!"],
        ),
    ]

    # Custom database URL override (optional)
    DATABASE_URL: Annotated[
        str,
        Field(
            default="",
            description="Custom database URL override",
            examples=[
                "postgresql://user:password@localhost:5432/tuxdb",
                "postgresql+psycopg://user:pass@host:5432/db",
            ],
        ),
    ]

    def get_database_url(self) -> str:
        """Get database URL, either custom or constructed from individual parts.

        Returns
        -------
        str
            Complete PostgreSQL database URL.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        # Construct from individual parts
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
