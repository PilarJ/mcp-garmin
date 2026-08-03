"""Garmin Connect session backed by tokens on disk.

`garminconnect` is synchronous, so every call is pushed to a worker thread —
otherwise one slow Garmin request would stall the whole MCP event loop.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

import anyio
from garminconnect import Garmin

logger = logging.getLogger(__name__)


class NotAuthorisedError(RuntimeError):
    """No usable Garmin tokens — the one-time interactive login has not run."""


class GarminClient:
    def __init__(self, token_dir: Path) -> None:
        self._token_dir = token_dir
        self._api: Garmin | None = None
        self._lock = anyio.Lock()
        self._profile_pk: str | None = None

    def _login_sync(self) -> Garmin:
        if not self._token_dir.exists():
            raise NotAuthorisedError(
                f"No Garmin tokens at {self._token_dir}. Run the one-time "
                "interactive login (`garmin-mcp-auth`) first."
            )
        api = Garmin()
        api.login(tokenstore=str(self._token_dir))
        logger.info("Garmin session established for %s", api.display_name)
        return api

    async def _session(self) -> Garmin:
        async with self._lock:
            if self._api is None:
                self._api = await anyio.to_thread.run_sync(self._login_sync)
            return self._api

    async def call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Invoke a garminconnect method by name, retrying once after re-login.

        Garmin expires sessions server-side without warning; a single retry on
        a refreshed session turns that from an error into a hiccup.
        """
        api = await self._session()
        fn: Callable[..., Any] = getattr(api, method)
        try:
            return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))
        except NotAuthorisedError:
            raise
        except Exception as exc:
            logger.warning("Garmin call %s failed (%s); re-authenticating", method, exc)
            async with self._lock:
                self._api = None
                self._profile_pk = None
            api = await self._session()
            fn = getattr(api, method)
            return await anyio.to_thread.run_sync(lambda: fn(*args, **kwargs))

    async def profile_pk(self) -> str:
        """Resolve the numeric profile id that the gear endpoints require.

        Garmin exposes it inconsistently, so try the documented keys in turn
        rather than assuming one shape.
        """
        if self._profile_pk:
            return self._profile_pk
        settings = await self.call("get_userprofile_settings")
        for key in ("id", "profileId", "userProfilePk", "userProfileId"):
            value = (settings or {}).get(key)
            if value:
                self._profile_pk = str(value)
                return self._profile_pk
        raise RuntimeError(
            "Could not determine the Garmin profile id from user settings; "
            "pass user_profile_number explicitly."
        )

    async def display_name(self) -> str | None:
        api = await self._session()
        return api.display_name

    def ready(self) -> bool:
        return self._token_dir.exists() and any(self._token_dir.iterdir())
