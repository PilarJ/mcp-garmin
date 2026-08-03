# mcp-garmin

An MCP server that exposes [Garmin Connect](https://connect.garmin.com/) over
Streamable HTTP, authenticated with GitHub OAuth.

It is built for **remote** use — as a custom connector in claude.ai / Claude
Desktop, or over `claude mcp add --transport http` — rather than as a local
stdio server. Two consequences follow from that:

- **Clients authenticate with OAuth**, handled by FastMCP's `GitHubProvider`.
  The server publishes `/.well-known/oauth-authorization-server` and supports
  Dynamic Client Registration, which is what claude.ai requires.
- **Garmin credentials never reach the client.** The interactive sign-in runs
  once; the resulting OAuth tokens live on a mounted volume and refresh
  themselves.

Data access is provided by [`garminconnect`](https://github.com/cyberjunky/python-garminconnect).

## Access control

Holding a valid GitHub identity is not enough. `ALLOWED_GITHUB_LOGINS` lists
the accounts permitted to use the server, and every message is checked against
it. If the list is empty the server refuses to start — an unset allowlist fails
closed rather than exposing health data to any GitHub user.

## Tools

**Diagnostics** — `garmin_status`

**Activities** — `garmin_get_activities`, `garmin_get_activities_by_date`,
`garmin_get_last_activity`, `garmin_get_activity`, `garmin_get_activity_splits`,
`garmin_get_activity_weather`, `garmin_get_activity_hr_zones`

**Analysis** — `garmin_compare_activities`, `garmin_get_progress_summary`

**Health** — `garmin_get_daily_summary`, `garmin_get_body_battery`,
`garmin_get_hrv`, `garmin_get_sleep`, `garmin_get_heart_rates`,
`garmin_get_resting_heart_rate`, `garmin_get_stress`, `garmin_get_steps`,
`garmin_get_spo2`, `garmin_get_respiration`

**Training** — `garmin_get_training_readiness`, `garmin_get_training_status`,
`garmin_get_max_metrics`, `garmin_get_hill_score`, `garmin_get_endurance_score`,
`garmin_get_race_predictions`, `garmin_get_training_summary`

**Profile, goals, gear** — `garmin_get_user_profile`,
`garmin_get_personal_records`, `garmin_get_goals`, `garmin_get_earned_badges`,
`garmin_get_badge_challenges`, `garmin_get_devices`, `garmin_get_gear`,
`garmin_get_gear_stats`

**Weight** — `garmin_get_weigh_ins`, `garmin_get_body_composition`

**Workouts** — `garmin_get_workouts`, `garmin_get_workout`,
`garmin_get_scheduled_workouts`

**Writes** — `garmin_upload_workout`, `garmin_schedule_workout`,
`garmin_create_manual_activity`, `garmin_add_weigh_in`,
`garmin_delete_activity`

Every write tool takes `confirm` and does nothing until it is `true`. These
change a real training record that feeds load and fitness metrics, so an
agent should show its intent and get agreement first rather than write
speculatively.

## Setup

### 1. GitHub OAuth app

Create one at **Settings → Developer settings → OAuth Apps** with the callback
URL `<BASE_URL>/auth/callback`. Copy the client id and secret.

### 2. Build and sign in to Garmin (once)

```bash
cp .env.example .env   # then fill it in
docker build -t mcp-garmin .

# Interactive: asks for password and any MFA code.
docker run -it --rm -v /srv/garmin-data:/data mcp-garmin garmin-mcp-auth
```

Tokens land in `/data/garminconnect` with mode `0600` and are refreshed
automatically from then on.

### 3. Run

```bash
docker run -d --name mcp-garmin --env-file .env \
  -v /srv/garmin-data:/data -p 8000:8000 mcp-garmin
```

### 4. Add the connector

- **Claude Code** — `claude mcp add --transport http garmin <BASE_URL>/mcp`
- **claude.ai / Claude Desktop** — Settings → Connectors → Add custom
  connector → `<BASE_URL>/mcp`

Both then send you through GitHub to sign in.

## Configuration

| Variable | Purpose |
|---|---|
| `BASE_URL` | Public URL of this server, no trailing slash |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth app credentials |
| `ALLOWED_GITHUB_LOGINS` | Comma-separated logins permitted to connect |
| `JWT_SIGNING_KEY` | Stable key for client tokens; unset means clients are signed out on restart |
| `DATA_DIR` | Where Garmin tokens live (default `/data`) |
| `GARMIN_EMAIL` / `GARMIN_PASSWORD` | Optional, only to pre-fill the interactive login |
| `HOST` / `PORT` | Bind address (default `0.0.0.0:8000`) |

## Notes

Garmin Connect has no public API; `garminconnect` talks to the endpoints the
mobile and web apps use, and Garmin changes them without notice. The dependency
is pinned exactly for that reason — upgrade deliberately and re-check the tools
afterwards.

Calls are synchronous, so each one runs in a worker thread; a slow Garmin
response cannot stall the MCP event loop. Sessions that Garmin expires
server-side are re-established once and the call retried.

## Licence

MIT
