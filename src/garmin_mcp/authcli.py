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
        # One attempt per run, deliberately. Garmin rate-limits its sign-in
        # endpoints per account, and the library's default of 3 turns a single
        # invocation into three strikes against that budget.
        retry_attempts=1,
    )

    try:
        api.login(tokenstore=str(token_dir))
    except Exception as exc:
        message = str(exc)
        if "429" in message or "rate limit" in message.lower():
            print(
                "\nGarmin is rate-limiting sign-in for this account (HTTP 429).\n"
                "\n"
                "This is not a wrong password — the attempt never reached the\n"
                "credential check. The limit is reported to be keyed on the\n"
                "account rather than the IP, so switching network or VPN does\n"
                "not clear it, and every further attempt extends the window.\n"
                "\n"
                "Wait roughly 24 hours, then run this once more. To check the\n"
                "account itself is healthy in the meantime, sign in at\n"
                "https://connect.garmin.com in a browser — the website uses a\n"
                "different limit bucket and normally still works.\n",
                file=sys.stderr,
            )
            return 2
        print(f"Login failed: {message}", file=sys.stderr)
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
