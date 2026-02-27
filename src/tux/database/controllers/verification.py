"""Verification controller for Roblox OAuth2 account linking."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from tux.database.controllers.base import BaseController
from tux.database.models import Verification

if TYPE_CHECKING:
    from tux.database.service import DatabaseService


class VerificationController(BaseController[Verification]):
    """Controller for verification-related database operations."""

    def __init__(self, db: DatabaseService | None = None) -> None:
        """Initialize the verification controller.

        Parameters
        ----------
        db : DatabaseService | None, optional
            The database service instance.
        """
        super().__init__(Verification, db)

    async def get_by_discord_id(self, discord_id: int) -> Verification | None:
        """Get a verification record by Discord ID."""
        return await self.find_one(filters=Verification.discord_id == discord_id)

    async def get_by_roblox_id(self, roblox_id: int) -> Verification | None:
        """Get a verification record by Roblox ID."""
        return await self.find_one(filters=Verification.roblox_id == roblox_id)

    async def upsert_verification(
        self,
        discord_id: int,
        roblox_id: int,
        roblox_username: str | None = None,
    ) -> Verification:
        """Create or update a verification record.

        Parameters
        ----------
        discord_id : int
            Discord user ID.
        roblox_id : int
            Roblox user ID.
        roblox_username : str | None, optional
            Roblox username.

        Returns
        -------
        Verification
            The created or updated verification record.
        """
        result, _ = await self.upsert(
            filters={"discord_id": discord_id},
            roblox_id=roblox_id,
            roblox_username=roblox_username,
            verified_at=datetime.now(UTC).replace(tzinfo=None),
        )
        return result

    async def delete(self, discord_id: int) -> bool:
        """Delete a verification record by Discord ID."""
        return await self.delete_by_id(discord_id)
