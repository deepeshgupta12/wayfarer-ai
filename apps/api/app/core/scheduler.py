"""
Background scheduler for proactive notifications.

Uses APScheduler's BackgroundScheduler (thread-based, no asyncio dependency)
so it integrates cleanly with a synchronous FastAPI / Uvicorn setup.

The scheduler runs one job on a fixed interval:
  _run_proactive_monitor_sweep
    – Queries all active/planning trips that haven't been inspected in the last
      MONITOR_INTERVAL_HOURS.
    – Fires `inspect_active_trip_alerts` for each, generating closure-risk,
      timing-conflict and quality-risk alerts in the background.
    – Completely silent on failure so it never takes down the API process.

The scheduler is started in main.py's lifespan context and shut down on exit.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

# How often the sweep runs (minutes between checks).
_SWEEP_INTERVAL_MINUTES = 30

# Minimum gap before re-inspecting the same trip (hours).
_REINSPECT_GAP_HOURS = 1

_scheduler = BackgroundScheduler(
    job_defaults={"coalesce": True, "max_instances": 1, "misfire_grace_time": 60},
    timezone="UTC",
)


def _run_proactive_monitor_sweep() -> None:
    """Inspect all active trips that are due for a freshness check."""
    # Imports are deferred to avoid circular import at module load time.
    from app.db.session import get_db_session  # noqa: PLC0415
    from app.models.proactive_alert import ProactiveAlertRecord  # noqa: PLC0415
    from app.models.saved_trip import SavedTripRecord  # noqa: PLC0415
    from app.schemas.live_runtime import ProactiveMonitorInspectRequest  # noqa: PLC0415
    from app.services.proactive_notification_service import inspect_active_trip_alerts  # noqa: PLC0415

    db = get_db_session()
    try:
        active_trips = (
            db.query(SavedTripRecord)
            .filter(SavedTripRecord.status.in_(["planning", "active", "upcoming"]))
            .all()
        )

        if not active_trips:
            return

        cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=_REINSPECT_GAP_HOURS)

        for trip in active_trips:
            # Skip if inspected recently.
            last_alert = (
                db.query(ProactiveAlertRecord)
                .filter(ProactiveAlertRecord.trip_id == trip.trip_id)
                .order_by(ProactiveAlertRecord.id.desc())
                .first()
            )
            if last_alert and last_alert.created_at.replace(tzinfo=timezone.utc) > cutoff:
                continue

            try:
                payload = ProactiveMonitorInspectRequest(
                    traveller_id=trip.traveller_id,
                    trip_id=trip.trip_id,
                    planning_session_id=trip.planning_session_id,
                    source_surface="background_scheduler",
                    current_day_only=False,
                    max_days_to_check=3,
                )
                inspect_active_trip_alerts(db, payload)
                logger.debug(
                    "Proactive sweep completed for trip_id=%s traveller_id=%s",
                    trip.trip_id,
                    trip.traveller_id,
                )
            except Exception as exc:  # pragma: no cover
                logger.warning(
                    "Proactive sweep failed for trip_id=%s: %s",
                    trip.trip_id,
                    exc,
                )
    except Exception as exc:  # pragma: no cover
        logger.warning("Proactive sweep DB query failed: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    """Start the background scheduler. Safe to call multiple times (idempotent)."""
    if _scheduler.running:
        return
    _scheduler.add_job(
        _run_proactive_monitor_sweep,
        trigger=IntervalTrigger(minutes=_SWEEP_INTERVAL_MINUTES),
        id="proactive_monitor_sweep",
        replace_existing=True,
    )
    _scheduler.start()
    logger.info(
        "Background scheduler started — proactive sweep every %d minutes.",
        _SWEEP_INTERVAL_MINUTES,
    )


def stop_scheduler() -> None:
    """Gracefully stop the scheduler on app shutdown."""
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped.")
