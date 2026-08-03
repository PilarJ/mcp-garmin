"""One-time interactive Garmin login.

Garmin has no headless credential flow: the first sign-in needs a real person
for the password and any MFA code. This writes the resulting OAuth tokens to
DATA_DIR/garminconnect, after which the server refreshes them on its own.

Run it attached to a terminal:

    docker run -it --rm -v /srv/garmin-data:/data mcp-garmin garmin-mcp-auth
"""

from __future__ import annotations

import getpass
import os
import sys
from pathlib import Path

from garminconnect import Garmin


def main() -> int:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    token_dir = data_dir / "garminconnect"
    token_dir.mkdir(parents=True, exist_ok=True)

    if not sys.stdin.isatty():
        print(
            "This command needs an interactive terminal (docker run -it).",
            file=sys.stderr,
        )
        return 1

    email = os.environ.get("GARMIN_EMAIL") or input("Garmin e-mail: ").strip()
    password = os.environ.get("GARMIN_PASSWORD") or getpass.getpass("Garmin password: ")

    api = Garmin(
        email=email,
        password=password,
        prompt_mfa=lambda: input("MFA code: ").strip(),
    )

    try:
        api.login(tokenstore=str(token_dir))
    except Exception as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1

    # login() writes the tokens itself; dump again so a partially-written
    # store from an interrupted attempt cannot survive.
    api.client.dump(str(token_dir))
    for path in token_dir.iterdir():
        os.chmod(path, 0o600)

    print(f"Logged in as {api.display_name}. Tokens stored in {token_dir}.")
    print("The server can now start; this step does not need repeating.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
