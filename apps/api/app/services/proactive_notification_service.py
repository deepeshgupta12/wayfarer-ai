from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.clients.google_places_client import GooglePlacesClient
from app.models.live_runtime import ActiveTripContextRecord
from app.models.proactive_alert import ProactiveAlertRecord
from app.models.saved_trip import SavedTripRecord, TripSignalRecord
from app.models.traveller_memory import TravellerMemoryRecord
from app.schemas.live_runtime import (
    ProactiveAlertListResponse,
    ProactiveAlertResolutionRequest,
    ProactiveAlertResponse,
    ProactiveMonitorInspectRequest,
    ProactiveMonitorInspectResponse,
)

from app.core.config import get_settings
from app.services.photo_intelligence_service import (
    build_visual_runtime_signal,
    enrich_place_payload_with_ranked_photos,
)

google_places_client = GooglePlacesClient()
settings = get_settings()

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_saved_trip_or_raise(db: Session, trip_id: str) -> SavedTripRecord:
    record = db.query(SavedTripRecord).filter(SavedTripRecord.trip_id == trip_id).first()
    if record is None:
        raise ValueError(f"Saved trip not found for trip_id={trip_id}")
    return record


def _get_live_context(db: Session, trip_id: str) -> ActiveTripContextRecord | None:
    return db.query(ActiveTripContextRecord).filter(ActiveTripContextRecord.trip_id == trip_id).first()


def _build_alert_response(record: ProactiveAlertRecord) -> ProactiveAlertResponse:
    return ProactiveAlertResponse(
        alert_id=record.alert_id,
        trip_id=record.trip_id,
        traveller_id=record.traveller_id,
        planning_session_id=record.planning_session_id,
        source_surface=record.source_surface,
        alert_type=record.alert_type,
        status=record.status,
        severity=record.severity,
        day_number=record.day_number,
        slot_type=record.slot_type,
        location_id=record.location_id,
        location_name=record.location_name,
        title=record.title,
        message=record.message,
        alternatives=list(record.alternatives or []),
        evidence=list(record.evidence or []),
        freshness_payload=dict(record.freshness_payload or {}),
        resolution_payload=dict(record.resolution_payload or {}),
        created_at=record.created_at,
        updated_at=record.updated_at,
        resolved_at=record.resolved_at,
    )


def _load_recent_signals(db: Session, trip_id: str, limit: int = 100) -> list[TripSignalRecord]:
    return (
        db.query(TripSignalRecord)
        .filter(TripSignalRecord.trip_id == trip_id)
        .order_by(desc(TripSignalRecord.created_at), desc(TripSignalRecord.id))
        .limit(limit)
        .all()
    )


def _candidate_map(saved_trip: SavedTripRecord) -> dict[str, dict]:
    items = list(saved_trip.current_candidate_places or [])
    return {str(item.get("location_id")): item for item in items if item.get("location_id")}

def _enrich_alert_alternative_with_visuals(
    db: Session,
    *,
    saved_trip: SavedTripRecord,
    alternative: dict,
) -> dict:
    parsed_constraints = dict(saved_trip.current_parsed_constraints or {})

    payload = enrich_place_payload_with_ranked_photos(
        db,
        payload=dict(alternative),
        traveller_id=saved_trip.traveller_id,
        traveller_type=parsed_constraints.get("group_type"),
        interests=list(parsed_constraints.get("interests") or []),
        context_tags=["alert_alternative", str(alternative.get("category") or "place")],
        limit=settings.photo_preview_limit,
    )

    photos = payload.get("photos") or []
    payload["visual_signal"] = build_visual_runtime_signal(
        photos=[photo for photo in []] if False else [
            # convert dicts back into PlacePhotoAsset-compatible shape lazily in consumer-facing payload
        ],
        place_name=str(payload.get("name") or "place"),
    )
    return payload


def _get_days_to_check(
    saved_trip: SavedTripRecord,
    live_context: ActiveTripContextRecord | None,
    payload: ProactiveMonitorInspectRequest,
) -> list[dict]:
    itinerary = list(saved_trip.current_itinerary_skeleton or [])
    if not itinerary:
        return []

    if payload.current_day_only and live_context and live_context.current_day_number:
        return [
            day
            for day in itinerary
            if int(day.get("day_number") or 0) == int(live_context.current_day_number)
        ]

    if live_context and live_context.current_day_number:
        start_day = int(live_context.current_day_number)
        end_day = start_day + payload.max_days_to_check - 1
        return [
            day
            for day in itinerary
            if start_day <= int(day.get("day_number") or 0) <= end_day
        ]

    return itinerary[: payload.max_days_to_check]


def _build_alternatives(
    db: Session,
    saved_trip: SavedTripRecord,
    slot: dict,
    current_location_id: str | None,
    candidate_lookup: dict[str, dict],
    max_items: int = 3,
) -> list[dict]:
    alternatives: list[dict] = []
    seen: set[str] = set()

    def append_item(raw_item: dict) -> bool:
        location_id = str(raw_item.get("location_id") or "")
        if not location_id or location_id == str(current_location_id or "") or location_id in seen:
            return False
        seen.add(location_id)

        enriched = _enrich_alert_alternative_with_visuals(
            db,
            saved_trip=saved_trip,
            alternative=raw_item,
        )
        alternatives.append(enriched)
        return len(alternatives) >= max_items

    for item in list(slot.get("alternatives") or []):
        if append_item(
            {
                "location_id": str(item.get("location_id") or ""),
                "name": item.get("name"),
                "city": item.get("city"),
                "country": item.get("country"),
                "category": item.get("category"),
                "score": item.get("score"),
                "why_alternative": item.get("why_alternative"),
                "source": "slot_alternative",
            }
        ):
            return alternatives

    for fallback_id in list(slot.get("fallback_candidate_ids") or []):
        fallback_id = str(fallback_id or "")
        if not fallback_id or fallback_id == str(current_location_id or "") or fallback_id in seen:
            continue
        candidate = candidate_lookup.get(fallback_id)
        if candidate is None:
            continue

        if append_item(
            {
                "location_id": fallback_id,
                "name": candidate.get("name"),
                "city": candidate.get("city"),
                "country": candidate.get("country"),
                "category": candidate.get("category"),
                "score": candidate.get("score"),
                "why_alternative": "Fallback candidate already attached to this slot.",
                "source": "slot_fallback",
            }
        ):
            return alternatives

    for location_id, candidate in candidate_lookup.items():
        if location_id == str(current_location_id or "") or location_id in seen:
            continue

        if append_item(
            {
                "location_id": location_id,
                "name": candidate.get("name"),
                "city": candidate.get("city"),
                "country": candidate.get("country"),
                "category": candidate.get("category"),
                "score": candidate.get("score"),
                "why_alternative": "Fallback recommendation from the active trip candidate pool.",
                "source": "trip_pool",
            }
        ):
            break

    return alternatives


def _find_existing_open_alert(
    db: Session,
    *,
    trip_id: str,
    alert_type: str,
    day_number: int | None,
    slot_type: str | None,
    location_id: str | None,
) -> ProactiveAlertRecord | None:
    query = (
        db.query(ProactiveAlertRecord)
        .filter(ProactiveAlertRecord.trip_id == trip_id)
        .filter(ProactiveAlertRecord.status == "generated")
        .filter(ProactiveAlertRecord.alert_type == alert_type)
    )

    if day_number is None:
        query = query.filter(ProactiveAlertRecord.day_number.is_(None))
    else:
        query = query.filter(ProactiveAlertRecord.day_number == day_number)

    if slot_type is None:
        query = query.filter(ProactiveAlertRecord.slot_type.is_(None))
    else:
        query = query.filter(ProactiveAlertRecord.slot_type == slot_type)

    if location_id is None:
        query = query.filter(ProactiveAlertRecord.location_id.is_(None))
    else:
        query = query.filter(ProactiveAlertRecord.location_id == location_id)

    return query.order_by(desc(ProactiveAlertRecord.updated_at), desc(ProactiveAlertRecord.id)).first()


def _upsert_generated_alert(
    db: Session,
    *,
    saved_trip: SavedTripRecord,
    payload: ProactiveMonitorInspectRequest,
    alert_type: str,
    severity: str,
    day_number: int | None,
    slot_type: str | None,
    location_id: str | None,
    location_name: str | None,
    title: str,
    message: str,
    alternatives: list[dict],
    evidence: list[dict],
    freshness_payload: dict,
) -> ProactiveAlertRecord:
    existing = _find_existing_open_alert(
        db,
        trip_id=saved_trip.trip_id,
        alert_type=alert_type,
        day_number=day_number,
        slot_type=slot_type,
        location_id=location_id,
    )

    if existing is None:
        record = ProactiveAlertRecord(
            alert_id=f"alert_{uuid4().hex}",
            trip_id=saved_trip.trip_id,
            traveller_id=saved_trip.traveller_id,
            planning_session_id=payload.planning_session_id or saved_trip.planning_session_id,
            source_surface=payload.source_surface,
            alert_type=alert_type,
            status="generated",
            severity=severity,
            day_number=day_number,
            slot_type=slot_type,
            location_id=location_id,
            location_name=location_name,
            title=title,
            message=message,
            alternatives=alternatives,
            evidence=evidence,
            freshness_payload=freshness_payload,
            resolution_payload={},
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    existing.severity = severity
    existing.title = title
    existing.message = message
    existing.alternatives = alternatives
    existing.evidence = evidence
    existing.freshness_payload = freshness_payload
    existing.source_surface = payload.source_surface
    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def inspect_active_trip_alerts(
    db: Session,
    payload: ProactiveMonitorInspectRequest,
) -> ProactiveMonitorInspectResponse:
    saved_trip = _get_saved_trip_or_raise(db, payload.trip_id)
    live_context = _get_live_context(db, payload.trip_id)
    recent_signals = _load_recent_signals(db, payload.trip_id, limit=100)
    candidate_lookup = _candidate_map(saved_trip)

    recent_signal_by_location: dict[str, list[TripSignalRecord]] = {}
    for signal in recent_signals:
        if signal.location_id:
            recent_signal_by_location.setdefault(str(signal.location_id), []).append(signal)

    generated_alerts: list[ProactiveAlertRecord] = []
    days_to_check = _get_days_to_check(saved_trip, live_context, payload)

    for day in days_to_check:
        day_number = int(day.get("day_number") or 0)
        slots = list(day.get("slots") or [])

        for slot in slots:
            slot_type = str(slot.get("slot_type") or "")
            assigned_location_id = str(slot.get("assigned_location_id") or "") or None
            assigned_place_name = str(slot.get("assigned_place_name") or "") or None

            alternatives = _build_alternatives(
                db,
                saved_trip,
                slot,
                assigned_location_id,
                candidate_lookup,
            )

            if not assigned_location_id:
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="fallback_gap",
                    severity="medium",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=None,
                    location_name=None,
                    title="Unassigned itinerary slot detected",
                    message=(
                        f"Day {day_number} {slot_type} has no assigned place, so the active plan has a gap "
                        "that should be resolved before the traveller discovers it manually."
                    ),
                    alternatives=alternatives,
                    evidence=[
                        {
                            "type": "slot_state",
                            "detail": "No assigned_location_id found for the monitored slot.",
                        }
                    ],
                    freshness_payload={},
                )
                generated_alerts.append(record)
                continue

            candidate = candidate_lookup.get(assigned_location_id, {})
            freshness = google_places_client.get_place_freshness(
                location_id=assigned_location_id,
                name=assigned_place_name or candidate.get("name"),
                city=candidate.get("city"),
                country=candidate.get("country"),
            )

            location_signals = recent_signal_by_location.get(assigned_location_id, [])
            blocker_signal = next(
                (
                    signal
                    for signal in location_signals
                    if signal.signal_type in {"place_closed", "place_unavailable"}
                ),
                None,
            )

            if blocker_signal is not None:
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="signal_blocker",
                    severity="high",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=assigned_location_id,
                    location_name=assigned_place_name or candidate.get("name"),
                    title="Recent blocker detected for an assigned place",
                    message=(
                        f"{assigned_place_name or candidate.get('name') or 'This place'} has a recent live blocker "
                        "signal, so the itinerary should be adapted before the active slot fails."
                    ),
                    alternatives=alternatives,
                    evidence=[
                        {
                            "type": "recent_signal",
                            "signal_type": blocker_signal.signal_type,
                            "created_at": blocker_signal.created_at.isoformat(),
                            "payload": dict(blocker_signal.payload or {}),
                        }
                    ],
                    freshness_payload=freshness,
                )
                generated_alerts.append(record)
                continue

            if str(freshness.get("operational_status") or "").lower() in {"temporarily_closed", "closed"}:
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="closure_risk",
                    severity="high",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=assigned_location_id,
                    location_name=assigned_place_name or candidate.get("name"),
                    title="Assigned place may be closed",
                    message=(
                        f"{assigned_place_name or candidate.get('name') or 'This place'} looks unavailable from the "
                        "freshness layer, so the itinerary should swap to an alternative."
                    ),
                    alternatives=alternatives,
                    evidence=[
                        {
                            "type": "freshness_status",
                            "operational_status": freshness.get("operational_status"),
                            "open_now": freshness.get("open_now"),
                        }
                    ],
                    freshness_payload=freshness,
                )
                generated_alerts.append(record)
                continue

            current_slot_matches_live_context = bool(
                live_context is not None
                and live_context.current_day_number == day_number
                and live_context.current_slot_type == slot_type
            )

            estimated_visit_minutes = int(freshness.get("estimated_visit_minutes") or 0)
            if (
                current_slot_matches_live_context
                and live_context is not None
                and live_context.available_minutes is not None
                and estimated_visit_minutes > int(live_context.available_minutes)
            ):
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="timing_conflict",
                    severity="medium",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=assigned_location_id,
                    location_name=assigned_place_name or candidate.get("name"),
                    title="Assigned place may not fit the live time window",
                    message=(
                        f"{assigned_place_name or candidate.get('name') or 'This place'} likely needs about "
                        f"{estimated_visit_minutes} minutes, which is longer than the traveller’s current "
                        f"available window of {live_context.available_minutes} minutes."
                    ),
                    alternatives=alternatives,
                    evidence=[
                        {
                            "type": "time_window_check",
                            "available_minutes": live_context.available_minutes,
                            "estimated_visit_minutes": estimated_visit_minutes,
                        }
                    ],
                    freshness_payload=freshness,
                )
                generated_alerts.append(record)
                continue

            quality_risk_score = float(freshness.get("quality_risk_score") or 0.0)
            quality_flags = list(freshness.get("quality_flags") or [])
            if quality_risk_score >= 0.35 or quality_flags:
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="quality_risk",
                    severity="medium",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=assigned_location_id,
                    location_name=assigned_place_name or candidate.get("name"),
                    title="Assigned place has freshness or quality risk",
                    message=(
                        f"{assigned_place_name or candidate.get('name') or 'This place'} shows freshness-layer risk "
                        "signals that may reduce the quality of the current itinerary slot."
                    ),
                    alternatives=alternatives,
                    evidence=[
                        {
                            "type": "quality_risk",
                            "quality_risk_score": quality_risk_score,
                            "quality_flags": quality_flags,
                        }
                    ],
                    freshness_payload=freshness,
                )
                generated_alerts.append(record)
                continue

            if not list(slot.get("alternatives") or []) and len(alternatives) == 0:
                record = _upsert_generated_alert(
                    db,
                    saved_trip=saved_trip,
                    payload=payload,
                    alert_type="fallback_gap",
                    severity="low",
                    day_number=day_number,
                    slot_type=slot_type,
                    location_id=assigned_location_id,
                    location_name=assigned_place_name or candidate.get("name"),
                    title="Assigned slot has weak fallback coverage",
                    message=(
                        f"Day {day_number} {slot_type} currently depends on "
                        f"{assigned_place_name or candidate.get('name') or 'a single place'} with no ready fallback."
                    ),
                    alternatives=[],
                    evidence=[
                        {
                            "type": "fallback_check",
                            "slot_alternative_count": len(list(slot.get("alternatives") or [])),
                            "fallback_candidate_count": len(list(slot.get("fallback_candidate_ids") or [])),
                        }
                    ],
                    freshness_payload=freshness,
                )
                generated_alerts.append(record)

    open_alert_count = (
        db.query(ProactiveAlertRecord)
        .filter(ProactiveAlertRecord.trip_id == payload.trip_id)
        .filter(ProactiveAlertRecord.status == "generated")
        .count()
    )

    generated_alerts_sorted = sorted(
        generated_alerts,
        key=lambda item: (
            {"high": 3, "medium": 2, "low": 1}.get(item.severity, 0),
            item.created_at,
        ),
        reverse=True,
    )

    return ProactiveMonitorInspectResponse(
        trip_id=payload.trip_id,
        traveller_id=payload.traveller_id,
        total=len(generated_alerts_sorted),
        generated_count=len(generated_alerts_sorted),
        open_alert_count=open_alert_count,
        alerts=[_build_alert_response(item) for item in generated_alerts_sorted],
        checked_at=_now(),
    )


def list_proactive_alerts(
    db: Session,
    trip_id: str,
    status: str | None = None,
    limit: int = 100,
) -> ProactiveAlertListResponse:
    _get_saved_trip_or_raise(db, trip_id)

    query = db.query(ProactiveAlertRecord).filter(ProactiveAlertRecord.trip_id == trip_id)
    if status:
        query = query.filter(ProactiveAlertRecord.status == status)

    records = (
        query.order_by(desc(ProactiveAlertRecord.updated_at), desc(ProactiveAlertRecord.id))
        .limit(limit)
        .all()
    )

    return ProactiveAlertListResponse(
        trip_id=trip_id,
        total=len(records),
        items=[_build_alert_response(record) for record in records],
    )


def resolve_proactive_alert(
    db: Session,
    alert_id: str,
    payload: ProactiveAlertResolutionRequest,
) -> ProactiveAlertResponse:
    record = db.query(ProactiveAlertRecord).filter(ProactiveAlertRecord.alert_id == alert_id).first()
    if record is None:
        raise ValueError(f"Proactive alert not found for alert_id={alert_id}")

    record.status = payload.status
    record.resolved_at = _now()
    record.resolution_payload = {
        "resolution_reason": payload.resolution_reason,
        "source_surface": payload.source_surface,
        **dict(payload.payload or {}),
    }

    db.add(record)

    memory_event = TravellerMemoryRecord(
        traveller_id=record.traveller_id,
        event_type=(
            "proactive_alert_resolved"
            if payload.status == "resolved"
            else "proactive_alert_ignored"
        ),
        source_surface=payload.source_surface,
        payload={
            "alert_id": record.alert_id,
            "trip_id": record.trip_id,
            "planning_session_id": record.planning_session_id,
            "alert_type": record.alert_type,
            "severity": record.severity,
            "day_number": record.day_number,
            "slot_type": record.slot_type,
            "location_id": record.location_id,
            "location_name": record.location_name,
            "resolution_reason": payload.resolution_reason,
            **dict(payload.payload or {}),
        },
    )
    db.add(memory_event)
    db.commit()
    db.refresh(record)

    return _build_alert_response(record)