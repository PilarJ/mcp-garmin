"""Configuration, loaded from environment / .env."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Public URL this server is reachable at (no trailing slash). ---
    base_url: str = Field(alias="BASE_URL")

    # --- Inbound auth: GitHub OAuth app used to authenticate MCP clients. ---
    github_client_id: str = Field(alias="GITHUB_CLIENT_ID")
    github_client_secret: str = Field(alias="GITHUB_CLIENT_SECRET")

    # Only these GitHub logins may use the server. Empty means nobody, on
    # purpose: an unset allowlist must fail closed, never open.
    # Kept as a raw string because pydantic-settings JSON-decodes list fields
    # straight out of the environment, which a comma-separated value fails.
    allowed_github_logins_raw: str = Field(default="", alias="ALLOWED_GITHUB_LOGINS")

    # Stable signing key for the tokens FastMCP issues to clients. Without it
    # a fresh key is generated per process, so every restart silently logs
    # every client out.
    jwt_signing_key: str | None = Field(default=None, alias="JWT_SIGNING_KEY")

    # Garmin OAuth tokens produced by the one-time `garmin-mcp-auth` run.
    data_dir: Path = Field(default=Path("/data"), alias="DATA_DIR")

    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    @field_validator("base_url")
    @classmethod
    def _strip_slash(cls, v: str) -> str:
        return v.rstrip("/")

    @property
    def allowed_github_logins(self) -> list[str]:
        return [
            item.strip()
            for item in self.allowed_github_logins_raw.split(",")
            if item.strip()
        ]

    @property
    def token_dir(self) -> Path:
        return self.data_dir / "garminconnect"


def load_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
