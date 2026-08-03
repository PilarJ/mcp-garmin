"""MCP server exposing Garmin Connect over Streamable HTTP."""

from __future__ import annotations

import logging

from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider

from . import tools
from .auth import GitHubAllowlistMiddleware
from .client import GarminClient
from .settings import Settings, load_settings

logger = logging.getLogger(__name__)


def build_server(settings: Settings) -> FastMCP:
    auth = GitHubProvider(
        client_id=settings.github_client_id,
        client_secret=settings.github_client_secret,
        base_url=settings.base_url,
        # Without a stable key, restarting the container invalidates every
        # token FastMCP has issued and all clients must sign in again.
        jwt_signing_key=settings.jwt_signing_key,
    )

    mcp = FastMCP(
        name="garmin",
        instructions=(
            "Access to the owner's Garmin Connect data: activities, sleep, "
            "HRV, Body Battery, training readiness and status, VO2 max, gear "
            "and weight. Dates are YYYY-MM-DD and default to today. "
            "Tools whose description starts with WRITE or DESTRUCTIVE change "
            "the user's real training record and do nothing unless "
            "confirm=true; ask the user before setting it."
        ),
        auth=auth,
    )
    mcp.add_middleware(GitHubAllowlistMiddleware(settings.allowed_github_logins))

    tools.register(mcp, GarminClient(settings.token_dir))
    return mcp


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = load_settings()

    if not settings.allowed_github_logins:
        # Fail loudly rather than serve health data to any GitHub account.
        raise SystemExit(
            "ALLOWED_GITHUB_LOGINS is empty. Set it to the GitHub logins that "
            "may use this server, otherwise the server is pointless: it would "
            "deny everyone."
        )

    mcp = build_server(settings)
    logger.info("Serving MCP at %s/mcp", settings.base_url)
    mcp.run(transport="http", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
