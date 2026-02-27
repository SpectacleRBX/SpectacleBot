"""Spectacle Studios Discord Servers - Verification Plugin."""

import base64
import hashlib
import secrets
from urllib.parse import quote

import discord
import httpx
from aiohttp import web
from discord import app_commands
from discord.ext import commands
from loguru import logger

from tux.core.base_cog import BaseCog
from tux.core.bot import Tux
from tux.services.http_client import http_client
from tux.shared.config import CONFIG


class Verify(BaseCog):
    """Manage and expose the verification functionality.

    This cog provides commands that allow users to verify their Discord accounts
    using Roblox OAuth2 and PKCE flow. It also runs a small web server to
    handle the OAuth2 callback.
    """

    def __init__(self, bot: Tux) -> None:
        super().__init__(bot)

        # In-memory fallback if cache_service is not available
        self._pending_verifications: dict[str, dict[str, int]] = {}
        self._verifiers: dict[str, str] = {}

        self.site_app = web.Application()
        self.site_app.add_routes([web.get("/callback", self.handle_callback)])
        self.site_runner: web.AppRunner | None = None

    async def cog_load(self) -> None:
        """Initialize the callback web server when the cog is loaded."""
        self.site_runner = web.AppRunner(self.site_app)
        await self.site_runner.setup()

        # Listen on 0.0.0.0 and the configured WEB_PORT
        site = web.TCPSite(self.site_runner, "0.0.0.0", CONFIG.WEB_PORT)
        await site.start()
        logger.info(f"Verification callback server listening on port {CONFIG.WEB_PORT}")

    async def cog_unload(self) -> None:
        """Clean up the web server when the cog is unloaded."""
        if self.site_runner:
            await self.site_runner.cleanup()
            logger.info("Verification callback server stopped")

    def generate_challenge(self) -> dict[str, str]:
        """Generate a random challenge and verifier for Roblox PKCE.

        Follows the S256 code challenge method.
        """
        # Create a URL-safe verifier (between 43 and 128 chars)
        verifier = secrets.token_urlsafe(64)

        # SHA256 hash the verifier
        hash_digest = hashlib.sha256(verifier.encode()).digest()

        # Base64URL encode the digest and remove padding (=)
        challenge = base64.urlsafe_b64encode(hash_digest).decode().replace("=", "")

        return {"verifier": verifier, "challenge": challenge}

    @commands.hybrid_command(name="link", aliases=["v", "verify"])
    @commands.guild_only()
    @app_commands.guild_only()
    async def link(self, ctx: commands.Context[Tux]) -> None:
        """Link your Discord account with Roblox to gain an XP boost."""
        # Check if already verified
        result = await self.bot.db.verification.get_by_discord_id(ctx.author.id)
        if result:
            await ctx.send(
                f"You are already verified as Roblox user **{result.roblox_username or result.roblox_id}**.",
                ephemeral=True,
            )
            return

        state = secrets.token_urlsafe(16)
        params = self.generate_challenge()

        # Store verification session data (valid for 10 minutes)
        cache = self.bot.cache_service.get_client() if self.bot.cache_service else None

        if cache:
            await cache.set(f"verify:discord_id:{state}", str(ctx.author.id), ex=600)
            if ctx.guild:
                await cache.set(f"verify:guild_id:{state}", str(ctx.guild.id), ex=600)
            await cache.set(f"verify:verifier:{state}", params["verifier"], ex=600)
        else:
            self._pending_verifications[state] = {
                "discord_id": ctx.author.id,
                "guild_id": ctx.guild.id if ctx.guild else 0,
            }
            self._verifiers[state] = params["verifier"]

        client_id = CONFIG.OAUTH2_CLIENTID
        redirect_uri = "http://localhost:5000/callback"
        scopes = "openid profile group:read"

        auth_url = (
            "https://apis.roblox.com/oauth/v1/authorize"
            f"?client_id={client_id}"
            f"&code_challenge={quote(params['challenge'])}"
            f"&code_challenge_method=S256"
            f"&redirect_uri={quote(redirect_uri)}"
            f"&scope={quote(scopes)}"
            f"&response_type=code"
            f"&state={quote(state)}"
        )

        await ctx.send(
            "To verify your Roblox account, please click the button below and follow the instructions.\n"
            "This link will expire in 10 minutes.",
            view=VerificationView(auth_url),
            ephemeral=True,
        )

    @commands.hybrid_command(name="unlink")
    @commands.guild_only()
    @app_commands.guild_only()
    async def unlink(self, ctx: commands.Context[Tux]) -> None:
        """Unlink your Discord account from Roblox."""
        result = await self.bot.db.verification.get_by_discord_id(ctx.author.id)
        if not result:
            await ctx.send(
                "You are not verified.",
                ephemeral=True,
            )
            return
        await self.bot.db.verification.delete(result.discord_id)
        await ctx.send(
            "Your Discord account has been unlinked from Roblox.",
            ephemeral=True,
        )

    async def handle_callback(self, request: web.Request) -> web.Response:
        """Handle the incoming OAuth2 callback from Roblox."""
        code = request.query.get("code")
        state = request.query.get("state")

        if not code or not state:
            return web.Response(
                text="Invalid callback: missing code or state.",
                status=400,
            )

        discord_id = None
        code_verifier = None

        # Retrieve session data
        cache = self.bot.cache_service.get_client() if self.bot.cache_service else None
        if cache:
            discord_id_val = await cache.get(f"verify:discord_id:{state}")
            discord_id = int(discord_id_val) if discord_id_val else None
            guild_id_val = await cache.get(f"verify:guild_id:{state}")
            guild_id = int(guild_id_val) if guild_id_val else None
            code_verifier = await cache.get(f"verify:verifier:{state}")

            # Clean up cache
            await cache.delete(f"verify:discord_id:{state}")
            await cache.delete(f"verify:guild_id:{state}")
            await cache.delete(f"verify:verifier:{state}")
        else:
            session = self._pending_verifications.pop(state, {})
            discord_id = session.get("discord_id")
            guild_id = session.get("guild_id")
            code_verifier = self._verifiers.pop(state, None)

        if not discord_id or not code_verifier or not guild_id:
            return web.Response(
                text="Verification session expired or invalid. Please run /verify again in Discord.",
                status=400,
            )

        try:
            # Exchange code for access token
            token_response = await http_client.post(
                "https://apis.roblox.com/oauth/v1/token",
                data={
                    "client_id": CONFIG.OAUTH2_CLIENTID,
                    "client_secret": CONFIG.OAUTH2_SECRET,
                    "grant_type": "authorization_code",
                    "code": code,
                    "code_verifier": code_verifier,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                logger.error(f"Failed to obtain Roblox access token: {token_data}")
                return web.Response(
                    text="Failed to authenticate with Roblox.",
                    status=500,
                )

            # Fetch Roblox user info
            user_response = await http_client.get(
                "https://apis.roblox.com/oauth/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            user_data = user_response.json()

            roblox_id = int(user_data["sub"])
            roblox_username = (
                user_data.get("preferred_username")
                or user_data.get("nickname")
                or str(roblox_id)
            )

            # Store the linkage in our database using the controller
            await self.bot.db.verification.upsert_verification(
                discord_id=discord_id,
                roblox_id=roblox_id,
                roblox_username=roblox_username,
            )

            logger.info(
                f"Verified Discord user {discord_id} as Roblox user {roblox_username} ({roblox_id})",
            )

            # Apply roles in all configured guilds
            await self._apply_roles(discord_id, roblox_id, access_token)

            user = self.bot.get_user(discord_id)
            name = user.name if user else "Unknown"

            return web.HTTPFound(
                f"https://spst.dev/verify?success=true&rbx={roblox_username}&dc={name}",
            )

        except Exception as e:
            logger.exception("Error during Roblox OAuth2 callback processing")
            return web.Response(text=f"An internal error occurred: {e}", status=500)

    async def _apply_roles(  # noqa: PLR0912
        self,
        discord_id: int,
        roblox_id: int,
        access_token: str,
    ) -> None:  # sourcery skip: low-code-quality
        """Apply verification roles to a user in all configured guilds."""
        group_check_cache: dict[int, bool] = {}

        for g_id, g_config in CONFIG.VERIFICATION.GUILDS.items():
            if g_id == 0:
                continue

            try:
                guild = self.bot.get_guild(g_id)
                if not guild:
                    continue

                try:
                    member = await guild.fetch_member(discord_id)
                except discord.NotFound:
                    continue
                except Exception as me:
                    logger.warning(
                        f"Failed to fetch member {discord_id} in guild {g_id}: {me}",
                    )
                    continue

                target_group_id = g_config.ROBLOX_GROUP_ID
                if target_group_id not in group_check_cache:
                    is_member = False
                    try:
                        resp = await http_client.get(
                            f"https://apis.roblox.com/cloud/v2/groups/{target_group_id}/memberships/users%2F{roblox_id}",
                            headers={"Authorization": f"Bearer {access_token}"},
                        )
                        if resp.status_code == 200:
                            is_member = True
                    except httpx.HTTPStatusError as ge:
                        if ge.response.status_code == 404:
                            logger.debug(
                                f"Roblox user {roblox_id} is not in group {target_group_id} (404).",
                            )
                        else:
                            logger.warning(
                                f"Roblox API error checking group {target_group_id}: {ge}",
                            )
                    except Exception as ge:
                        logger.warning(
                            f"Failed to check group membership for {target_group_id}: {ge}",
                        )
                    group_check_cache[target_group_id] = is_member

                is_group_member = group_check_cache.get(target_group_id, False)
                roles_to_add: list[discord.Role] = []

                if (v_role_id := g_config.VERIFIED_ROLE_ID) and (
                    v_role := guild.get_role(v_role_id)
                ):
                    roles_to_add.append(v_role)

                if (
                    is_group_member
                    and (g_role_id := g_config.GROUP_MEMBER_ROLE_ID)
                    and (g_role := guild.get_role(g_role_id))
                ):
                    roles_to_add.append(g_role)

                if roles_to_add:  # noqa: SIM102
                    if to_add := [r for r in roles_to_add if r not in member.roles]:
                        await member.add_roles(*to_add, reason="Roblox Verification")
                        logger.info(f"Added roles {to_add} to {member} in {guild.name}")

            except Exception as e:
                logger.warning(f"Error processing roles for guild {g_id}: {e}")

    def _get_success_html(self, username: str) -> str:
        """Return a simple HTML success page."""
        return f"""
        <html>
            <head>
                <title>Verification Successful</title>
                <style>
                    body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; background: #121212; color: #fff; }}
                    .container {{ text-align: center; padding: 2rem; background: #1e1e1e; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.5); }}
                    h1 {{ color: #00ff00; }}
                    strong {{ color: #00aaff; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Verification Successful!</h1>
                    <p>You have been verified as <strong>{username}</strong>.</p>
                    <p>You can now close this window and return to Discord.</p>
                </div>
            </body>
        </html>
        """


class VerificationView(discord.ui.View):
    """Simple view with a button that links to the Roblox OAuth2 URL."""

    def __init__(self, url: str) -> None:
        super().__init__()
        self.add_item(
            discord.ui.Button(
                label="Verify with Roblox",
                url=url,
                style=discord.ButtonStyle.link,
            ),
        )


async def setup(bot: Tux) -> None:
    """Register the verify cog with the bot."""
    await bot.add_cog(Verify(bot))
