"""
Logging service for tracking message edits and deletions.

This module implements a logging system that sends message delete and edit events
to a designated private log channel, helping moderators track changes.
"""

import discord
from discord.ext import commands

from tux.core.base_cog import BaseCog
from tux.core.bot import Tux
from tux.ui.embeds import EmbedCreator, EmbedType


class Logging(BaseCog):
    """Discord cog for logging message events.

    This cog monitors message deletions and edits and logs them to the
    configured private log channel for the guild.
    """

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Handle message delete events.

        Parameters
        ----------
        message : discord.Message
            The message that was deleted.
        """
        # Skip bots, DMs, and non-guild channels to ensure channel has .mention
        if (
            message.author.bot
            or not message.guild
            or not isinstance(message.channel, discord.abc.GuildChannel)
        ):
            return

        # Skip if maintenance mode is enabled
        if getattr(self.bot, "maintenance_mode", False):
            return

        private_log_id = await self.db.guild_config.get_private_log_id(message.guild.id)
        if not private_log_id:
            return

        channel = message.guild.get_channel(private_log_id)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = EmbedCreator.create_embed(
            embed_type=EmbedType.INFO,
            title="Message Deleted",
            description=(
                f"**Author:** {message.author.mention} (`{message.author.id}`)\n"
                f"**Channel:** {message.channel.mention} (`{message.channel.id}`)\n\n"
                f"**Content:**\n{message.content or '*No content (attachment or embed only)*'}"
            ),
            custom_author_text=str(message.author),
            custom_author_icon_url=message.author.display_avatar.url,
            message_timestamp=discord.utils.utcnow(),
        )

        # Handle attachments
        if message.attachments:
            attachment_info = "\n".join(
                [f"[{a.filename}]({a.url})" for a in message.attachments],
            )
            embed.add_field(name="Attachments", value=attachment_info, inline=False)

        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message,
    ) -> None:
        """Handle message edit events.

        Parameters
        ----------
        before : discord.Message
            The message state before the edit.
        after : discord.Message
            The message state after the edit.
        """
        # Skip bots, DMs, and non-guild channels to ensure channel has .mention
        if (
            before.author.bot
            or not before.guild
            or not isinstance(before.channel, discord.abc.GuildChannel)
        ):
            return

        # Skip if content didn't change (e.g. only embeds/pins changed)
        if before.content == after.content:
            return

        # Skip if maintenance mode is enabled
        if getattr(self.bot, "maintenance_mode", False):
            return

        private_log_id = await self.db.guild_config.get_private_log_id(before.guild.id)
        if not private_log_id:
            return

        channel = before.guild.get_channel(private_log_id)
        if not isinstance(channel, discord.TextChannel):
            return

        embed = EmbedCreator.create_embed(
            embed_type=EmbedType.INFO,
            title="Message Edited",
            description=(
                f"**Author:** {before.author.mention} (`{before.author.id}`)\n"
                f"**Channel:** {before.channel.mention} (`{before.channel.id}`)\n"
                f"**Jump:** [Click here to jump]({after.jump_url})"
            ),
            custom_author_text=str(before.author),
            custom_author_icon_url=before.author.display_avatar.url,
            message_timestamp=discord.utils.utcnow(),
        )

        # Truncate content to fit in embed fields (max 1024 chars)
        def truncate(text: str) -> str:
            return (text[:1021] + "...") if len(text) > 1024 else text

        embed.add_field(
            name="Before",
            value=truncate(before.content or "*No content*"),
            inline=False,
        )
        embed.add_field(
            name="After",
            value=truncate(after.content or "*No content*"),
            inline=False,
        )

        await channel.send(embed=embed)


async def setup(bot: Tux) -> None:
    """Set up the Logging cog.

    Parameters
    ----------
    bot : Tux
        The bot instance.
    """
    await bot.add_cog(Logging(bot))
