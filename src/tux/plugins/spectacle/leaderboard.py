"""Spectacle Studios Discord Servers - XP Leaderboard Plugin."""

import discord
from discord import app_commands
from discord.ext import commands

from tux.core.base_cog import BaseCog
from tux.core.bot import Tux
from tux.modules.features.levels import LevelsService
from tux.ui.embeds import EmbedCreator, EmbedType


class Leaderboard(BaseCog):
    """Manage and expose the XP leaderboard functionality.

    This cog provides commands that allow users to view XP rankings and related
    leaderboard information within the Discord server.
    """

    def __init__(self, bot: Tux) -> None:
        super().__init__(bot)

        self.levels_service = LevelsService(bot)

    @commands.command(name="leaderboard", aliases=["lb", "top"])
    @app_commands.guild_only()
    async def leaderboard(self, ctx: commands.Context[Tux]) -> None:
        """Show the XP leaderboard for the current Discord server.

        This command responds with a placeholder message until the leaderboard
        functionality is fully implemented.
        """
        await ctx.defer()

        top_members = await self.levels_service.db.levels.get_top_members(0, 10)
        embed = EmbedCreator.create_embed(
            embed_type=EmbedType.INFO,
            title="XP Leaderboard",
            message_timestamp=discord.utils.utcnow(),
        )
        for member in top_members:
            try:
                user = await self.bot.fetch_user(member.member_id)
                embed.add_field(
                    name=f"{user.name}",
                    value=f"{int(member.xp):,d}",
                    inline=False,
                )
            except discord.NotFound:
                embed.add_field(
                    name="Unknown user",
                    value=f"{int(member.xp):,d}",
                    inline=False,
                )

        await ctx.send(embed=embed)


async def setup(bot: Tux) -> None:
    """Register the leaderboard cog with the bot.

    This function initializes the leaderboard plugin and adds it to the running bot instance.
    """
    await bot.add_cog(Leaderboard(bot))
