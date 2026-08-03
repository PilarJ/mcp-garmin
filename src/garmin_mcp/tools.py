"""MCP tools over Garmin Connect."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from .client import GarminClient

CDate = Annotated[
    str | None,
    Field(description="Date as YYYY-MM-DD. Defaults to today when omitted."),
]
StartDate = Annotated[str, Field(description="Start date as YYYY-MM-DD.")]
EndDate = Annotated[
    str | None, Field(description="End date as YYYY-MM-DD. Defaults to today.")
]
ActivityId = Annotated[str, Field(description="Garmin activity id.")]
Confirm = Annotated[
    bool,
    Field(
        description="Must be true to actually perform this write. "
        "Ask the user before setting it."
    ),
]

REFUSED = {
    "status": "refused",
    "detail": "This tool changes data in Garmin Connect. Re-run with confirm=true "
    "once the user has agreed.",
}


def _day(value: str | None) -> str:
    return value or date.today().isoformat()


def _end(value: str | None) -> str:
    return value or date.today().isoformat()


def register(mcp: FastMCP, garmin: GarminClient) -> None:
    # ---------------- diagnostics ----------------

    @mcp.tool
    async def garmin_status() -> dict:
        """Report whether the server holds a usable Garmin Connect session.

        Use this first when other tools fail — it distinguishes "not logged in
        to Garmin" from a genuine API error.
        """
        if not garmin.ready():
            return {
                "connected": False,
                "detail": "No Garmin tokens stored; the one-time interactive "
                "login has not been run.",
            }
        return {"connected": True, "display_name": await garmin.display_name()}

    # ---------------- activities ----------------

    @mcp.tool
    async def garmin_get_activities(
        limit: Annotated[int, Field(ge=1, le=100)] = 20,
        start: Annotated[int, Field(ge=0, description="Offset for paging.")] = 0,
        activity_type: Annotated[
            str | None,
            Field(description="Filter, e.g. running, cycling, swimming, strength."),
        ] = None,
    ) -> Any:
        """List recent activities, newest first."""
        return await garmin.call("get_activities", start, limit, activity_type)

    @mcp.tool
    async def garmin_get_activities_by_date(
        start_date: StartDate,
        end_date: EndDate = None,
        activity_type: str | None = None,
    ) -> Any:
        """List activities within a date range."""
        return await garmin.call(
            "get_activities_by_date", start_date, _end(end_date), activity_type
        )

    @mcp.tool
    async def garmin_get_last_activity() -> Any:
        """Get the most recent activity."""
        return await garmin.call("get_last_activity")

    @mcp.tool
    async def garmin_get_activity(activity_id: ActivityId) -> Any:
        """Get full detail for one activity, including summary metrics."""
        return await garmin.call("get_activity", activity_id)

    @mcp.tool
    async def garmin_get_activity_splits(activity_id: ActivityId) -> Any:
        """Get lap/split breakdown for an activity."""
        return await garmin.call("get_activity_splits", activity_id)

    @mcp.tool
    async def garmin_get_activity_weather(activity_id: ActivityId) -> Any:
        """Get the weather recorded during an activity."""
        return await garmin.call("get_activity_weather", activity_id)

    @mcp.tool
    async def garmin_get_activity_hr_zones(activity_id: ActivityId) -> Any:
        """Get time spent in each heart-rate zone during an activity."""
        return await garmin.call("get_activity_hr_in_timezones", activity_id)

    # ---------------- analysis ----------------

    @mcp.tool
    async def garmin_compare_activities(
        activity_id_a: ActivityId, activity_id_b: ActivityId
    ) -> dict:
        """Fetch two activities side by side for comparison."""
        return {
            "a": await garmin.call("get_activity", activity_id_a),
            "b": await garmin.call("get_activity", activity_id_b),
        }

    @mcp.tool
    async def garmin_get_progress_summary(
        start_date: StartDate,
        end_date: EndDate = None,
        metric: Annotated[
            str,
            Field(description="One of: distance, duration, elevationGain, calories."),
        ] = "distance",
    ) -> Any:
        """Summarise progress for a metric across a date range, by activity type."""
        return await garmin.call(
            "get_progress_summary_between_dates", start_date, _end(end_date), metric
        )

    # ---------------- health and wellness ----------------

    @mcp.tool
    async def garmin_get_daily_summary(cdate: CDate = None) -> Any:
        """Get the all-day summary: steps, calories, intensity minutes, stress."""
        return await garmin.call("get_user_summary", _day(cdate))

    @mcp.tool
    async def garmin_get_body_battery(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """Get Body Battery (energy) readings across a date range."""
        return await garmin.call("get_body_battery", start_date, _end(end_date))

    @mcp.tool
    async def garmin_get_hrv(cdate: CDate = None) -> Any:
        """Get overnight heart-rate variability, including the HRV status."""
        return await garmin.call("get_hrv_data", _day(cdate))

    @mcp.tool
    async def garmin_get_sleep(cdate: CDate = None) -> Any:
        """Get sleep for a night: stages, duration, and sleep score."""
        return await garmin.call("get_sleep_data", _day(cdate))

    @mcp.tool
    async def garmin_get_heart_rates(cdate: CDate = None) -> Any:
        """Get the heart-rate curve for a day, plus resting heart rate."""
        return await garmin.call("get_heart_rates", _day(cdate))

    @mcp.tool
    async def garmin_get_resting_heart_rate(cdate: CDate = None) -> Any:
        """Get resting heart rate for a day."""
        return await garmin.call("get_rhr_day", _day(cdate))

    @mcp.tool
    async def garmin_get_stress(cdate: CDate = None) -> Any:
        """Get the all-day stress curve."""
        return await garmin.call("get_stress_data", _day(cdate))

    @mcp.tool
    async def garmin_get_steps(cdate: CDate = None) -> Any:
        """Get intraday step counts."""
        return await garmin.call("get_steps_data", _day(cdate))

    @mcp.tool
    async def garmin_get_spo2(cdate: CDate = None) -> Any:
        """Get pulse oximetry (blood oxygen saturation) readings."""
        return await garmin.call("get_spo2_data", _day(cdate))

    @mcp.tool
    async def garmin_get_respiration(cdate: CDate = None) -> Any:
        """Get respiration rate readings."""
        return await garmin.call("get_respiration_data", _day(cdate))

    # ---------------- training ----------------

    @mcp.tool
    async def garmin_get_training_readiness(cdate: CDate = None) -> Any:
        """Get the training readiness score and the factors behind it."""
        return await garmin.call("get_training_readiness", _day(cdate))

    @mcp.tool
    async def garmin_get_training_status(cdate: CDate = None) -> Any:
        """Get training status, load balance and acute/chronic load."""
        return await garmin.call("get_training_status", _day(cdate))

    @mcp.tool
    async def garmin_get_max_metrics(cdate: CDate = None) -> Any:
        """Get VO2 max and fitness age metrics."""
        return await garmin.call("get_max_metrics", _day(cdate))

    @mcp.tool
    async def garmin_get_hill_score(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """Get hill score (climbing strength and endurance) over a range."""
        return await garmin.call("get_hill_score", start_date, _end(end_date))

    @mcp.tool
    async def garmin_get_endurance_score(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """Get endurance score over a range."""
        return await garmin.call("get_endurance_score", start_date, _end(end_date))

    @mcp.tool
    async def garmin_get_race_predictions() -> Any:
        """Get predicted race times for 5k, 10k, half and full marathon."""
        return await garmin.call("get_race_predictions")

    @mcp.tool
    async def garmin_get_training_summary(days: Annotated[int, Field(ge=1, le=30)] = 7) -> dict:
        """Pull readiness, status, VO2 max and recent activities in one call.

        Convenience for "how is my training going" questions, which otherwise
        need four separate round trips.
        """
        today = date.today()
        since = (today - timedelta(days=days)).isoformat()
        return {
            "days": days,
            "readiness": await garmin.call("get_training_readiness", today.isoformat()),
            "status": await garmin.call("get_training_status", today.isoformat()),
            "max_metrics": await garmin.call("get_max_metrics", today.isoformat()),
            "activities": await garmin.call(
                "get_activities_by_date", since, today.isoformat(), None
            ),
        }

    # ---------------- profile, goals, gear ----------------

    @mcp.tool
    async def garmin_get_user_profile() -> Any:
        """Get the Garmin Connect user profile."""
        return await garmin.call("get_user_profile")

    @mcp.tool
    async def garmin_get_personal_records() -> Any:
        """Get personal records (fastest 5k, longest ride, and so on)."""
        return await garmin.call("get_personal_record")

    @mcp.tool
    async def garmin_get_goals(
        status: Annotated[str, Field(description="active, future or past.")] = "active",
    ) -> Any:
        """Get training goals."""
        return await garmin.call("get_goals", status, 0, 30)

    @mcp.tool
    async def garmin_get_earned_badges() -> Any:
        """Get badges already earned."""
        return await garmin.call("get_earned_badges")

    @mcp.tool
    async def garmin_get_badge_challenges() -> Any:
        """Get badge challenges currently in progress."""
        return await garmin.call("get_badge_challenges", 0, 30)

    @mcp.tool
    async def garmin_get_devices() -> Any:
        """List registered Garmin devices."""
        return await garmin.call("get_devices")

    @mcp.tool
    async def garmin_get_gear(
        user_profile_number: Annotated[
            str | None,
            Field(description="Override the auto-detected Garmin profile id."),
        ] = None,
    ) -> Any:
        """List gear (shoes, bikes) registered to the account."""
        pk = user_profile_number or await garmin.profile_pk()
        return await garmin.call("get_gear", pk)

    @mcp.tool
    async def garmin_get_gear_stats(gear_uuid: str) -> Any:
        """Get accumulated distance and usage stats for one piece of gear."""
        return await garmin.call("get_gear_stats", gear_uuid)

    # ---------------- weight ----------------

    @mcp.tool
    async def garmin_get_weigh_ins(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """Get weigh-ins across a date range."""
        return await garmin.call("get_weigh_ins", start_date, _end(end_date))

    @mcp.tool
    async def garmin_get_body_composition(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """Get body composition (weight, body fat, muscle mass) across a range."""
        return await garmin.call("get_body_composition", start_date, _end(end_date))

    # ---------------- workouts ----------------

    @mcp.tool
    async def garmin_get_workouts(
        limit: Annotated[int, Field(ge=1, le=100)] = 25,
    ) -> Any:
        """List saved structured workouts."""
        return await garmin.call("get_workouts", 0, limit)

    @mcp.tool
    async def garmin_get_workout(workout_id: str) -> Any:
        """Get one saved workout by id."""
        return await garmin.call("get_workout_by_id", workout_id)

    @mcp.tool
    async def garmin_get_scheduled_workouts(
        start_date: StartDate, end_date: EndDate = None
    ) -> Any:
        """List workouts scheduled on the calendar in a date range."""
        return await garmin.call("get_scheduled_workouts", start_date, _end(end_date))

    # ---------------- writes ----------------
    # Every tool below changes data in the user's real Garmin account, so each
    # one refuses to act until confirm=true is passed.

    @mcp.tool
    async def garmin_upload_workout(
        workout_json: Annotated[
            dict,
            Field(
                description="A Garmin Connect workout object: workoutName, "
                "sportType and workoutSegments with workoutSteps."
            ),
        ],
        confirm: Confirm = False,
    ) -> Any:
        """WRITE. Create a structured workout in Garmin Connect.

        The workout appears in the user's real training calendar. Show the
        planned workout to the user and get agreement before confirming.
        """
        if not confirm:
            return REFUSED
        return await garmin.call("upload_workout", workout_json)

    @mcp.tool
    async def garmin_schedule_workout(
        workout_id: str,
        cdate: Annotated[str, Field(description="Date to schedule on, YYYY-MM-DD.")],
        confirm: Confirm = False,
    ) -> Any:
        """WRITE. Put an existing workout on the calendar for a given date."""
        if not confirm:
            return REFUSED
        return await garmin.call("schedule_workout", workout_id, cdate)

    @mcp.tool
    async def garmin_create_manual_activity(
        start_datetime: Annotated[
            str, Field(description="Local start time, e.g. 2026-08-03T18:30:00.")
        ],
        time_zone: Annotated[str, Field(description="IANA zone, e.g. Europe/Prague.")],
        type_key: Annotated[
            str, Field(description="Activity type key, e.g. running, cycling.")
        ],
        distance_km: float,
        duration_min: int,
        activity_name: str,
        confirm: Confirm = False,
    ) -> Any:
        """WRITE. Add an activity to the user's Garmin history by hand.

        This becomes part of the permanent training record and affects load and
        fitness metrics, so never invent the values.
        """
        if not confirm:
            return REFUSED
        return await garmin.call(
            "create_manual_activity",
            start_datetime,
            time_zone,
            type_key,
            distance_km,
            duration_min,
            activity_name,
        )

    @mcp.tool
    async def garmin_add_weigh_in(
        weight: float,
        unit: Annotated[str, Field(description="kg or lbs.")] = "kg",
        timestamp: Annotated[
            str, Field(description="Optional ISO timestamp; blank means now.")
        ] = "",
        confirm: Confirm = False,
    ) -> Any:
        """WRITE. Record a weigh-in."""
        if not confirm:
            return REFUSED
        return await garmin.call("add_weigh_in", weight, unit, timestamp)

    @mcp.tool
    async def garmin_delete_activity(
        activity_id: ActivityId, confirm: Confirm = False
    ) -> Any:
        """DESTRUCTIVE. Permanently delete an activity from Garmin Connect.

        There is no undo. Confirm the exact activity with the user first.
        """
        if not confirm:
            return REFUSED
        return await garmin.call("delete_activity", activity_id)
