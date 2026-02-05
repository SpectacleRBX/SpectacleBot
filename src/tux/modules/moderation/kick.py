"""
Kick moderation command for Tux Bot.

This module provides the kick command functionality, allowing server
moderators to kick users from the server.
"""

import discord
from discord.ext import commands

from tux.core.bot import Tux
from tux.core.checks import requires_command_permission
from tux.core.flags import KickFlags
from tux.database.models import CaseType as DBCaseType

from . import ModerationCogBase


class Kick(ModerationCogBase):
    """Kick command cog for moderating server members."""

    def __init__(self, bot: Tux) -> None:
        """Initialize the Kick cog.

        Parameters
        ----------
        bot : Tux
            The bot instance to initialize the cog with.
        """
        super().__init__(bot)

    @commands.hybrid_command(
        name="kick",
        aliases=["k"],
    )
    @commands.guild_only()
    @requires_command_permission()
    async def kick(
        self,
        ctx: commands.Context[Tux],
        member: discord.Member | discord.User,
        *,
        flags: KickFlags,
    ) -> None:
        """
        Kick a member from the server.

        Parameters
        ----------
        ctx : commands.Context[Tux]
            The context in which the command is being invoked.
        member : discord.Member
            The member to kick.
        flags : KickFlags
            The flags for the command. (reason: str, silent: bool)
        """
        assert ctx.guild

        # Defer early to acknowledge interaction before async work
        if ctx.interaction and not ctx.interaction.response.is_done():
            await ctx.defer(ephemeral=True)

        # Validate that the target is a member of the guild
        if not isinstance(member, discord.Member):
            await self._respond(ctx, f"User {member} is not a member of this server.")
            return

        # Execute kick with case creation and DM
        await self.moderate_user(
            ctx=ctx,
            case_type=DBCaseType.KICK,
            user=member,
            reason=flags.reason,
            silent=flags.silent,
            dm_action="kicked",
            actions=[
                (
                    lambda: ctx.guild.kick(member, reason=flags.reason)
                    if ctx.guild
                    else None,
                    type(None),
                ),
            ],
        )


async def setup(bot: Tux) -> None:
    """Set up the Kick cog.

    Parameters
    ----------
    bot : Tux
        The bot instance to add the cog to.
    """
    await bot.add_cog(Kick(bot))
