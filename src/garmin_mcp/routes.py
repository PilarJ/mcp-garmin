"""Non-MCP HTTP routes."""

from __future__ import annotations

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from .settings import Settings


def register(mcp: FastMCP, settings: Settings) -> None:
    @mcp.custom_route("/", methods=["GET", "POST"])
    async def index(request: Request) -> Response:
        """Say where the MCP endpoint actually is.

        Clients configured with the bare domain land here and get a bare 404,
        which surfaces as "no MCP server was found at the provided URL" — true
        but easy to misread as a permissions problem.
        """
        return HTMLResponse(
            "<!doctype html><meta charset=utf-8><title>Garmin MCP server</title>"
            "<body style='font-family:system-ui;max-width:40em;margin:4em auto'>"
            "<h1>Garmin MCP server</h1>"
            f"<p>This is an MCP server. The endpoint is "
            f"<code>{settings.base_url}/mcp</code> — configure your client with "
            f"that full URL, including the <code>/mcp</code> suffix.</p></body>",
            status_code=404,
        )
