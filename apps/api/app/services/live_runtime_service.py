from __future__ import annotations

import json
import re
from collections.abc import Generator
from datetime import datetime, timezone
from statistics import median
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.live_runtime import (
    ActiveTripContextRecord,
    AgentGraphEventRecord,
    AgentGraphRunRecord,
)
from app.models.saved_trip import SavedTripRecord, TripSignalRecord
from app.models.traveller_memory import TravellerMemoryRecord
from app.schemas.destination import NearbyDiscoveryContext, NearbyDiscoveryRequest
from app.schemas.live_runtime import (
    AgentGraphEventListResponse,
    AgentGraphEventResponse,
    AgentGraphRunResponse,
    LiveActionWriteRequest,
    LiveActionWriteResponse,
    LiveRuntimeOrchestrateRequest,
    LiveRuntimeOrchestrateResponse,
    LiveTripContextResponse,
    LiveTripContextUpsertRequest,
    ProactiveMonitorInspectRequest,
)
from app.services.nearby_discovery_service import discover_context_aware_nearby_places
from app.services.proactive_notification_service import inspect_active_trip_alerts
from app.services.persona_embedding_service import calculate_persona_relevance_score

_CHECKPOINTER = MemorySaver()
_MAX_NEARBY_RESULTS = 5
_MAX_GEM_RESULTS = 5


class LiveGraphState(TypedDict, total=False):
    run_id: str
    traveller_id: str
    trip_id: str
    planning_session_id: str | None
    source_surface: str
    message: str
    live_context: dict[str, Any]
    saved_trip: dict[str, Any]
    recent_signals: list[dict[str, Any]]
    recent_memories: list[dict[str, Any]]
    supervisor: dict[str, Any]
    routed_agent: str
    result: dict[str, Any]
    proactive_alerts: list[dict[str, Any]]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _json_safe(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value

def _merge_live_context_dicts(
    persisted: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any]:
    base = dict(persisted or {})
    incoming = dict(override or {})

    if not incoming:
        return base

    merged = {**base, **incoming}

    base_payload = dict(base.get("context_payload") or {})
    incoming_payload = dict(incoming.get("context_payload") or {})
    merged["context_payload"] = {**base_payload, **incoming_payload}

    return merged


def _build_live_context_response(record: ActiveTripContextRecord) -> LiveTripContextResponse:
    return LiveTripContextResponse(
        trip_id=record.trip_id,
        traveller_id=record.traveller_id,
        planning_session_id=record.planning_session_id,
        source_surface=record.source_surface,
        trip_status=record.trip_status,
        intent_hint=record.intent_hint,
        transport_mode=record.transport_mode,
        budget_level_override=record.budget_level_override,
        available_minutes=record.available_minutes,
        current_day_number=record.current_day_number,
        current_slot_type=record.current_slot_type,
        latitude=record.latitude,
        longitude=record.longitude,
        accuracy_meters=record.accuracy_meters,
        local_time_iso=record.local_time_iso,
        timezone=record.timezone,
        current_place_name=record.current_place_name,
        current_city=record.current_city,
        current_country=record.current_country,
        context_payload=dict(record.context_payload or {}),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _build_graph_run_response(record: AgentGraphRunRecord) -> AgentGraphRunResponse:
    return AgentGraphRunResponse(
        run_id=record.run_id,
        traveller_id=record.traveller_id,
        trip_id=record.trip_id,
        planning_session_id=record.planning_session_id,
        source_surface=record.source_surface,
        user_message=record.user_message,
        status=record.status,
        routed_agent=record.routed_agent,
        supervisor_intent=record.supervisor_intent,
        checkpoint_thread_id=record.checkpoint_thread_id,
        graph_state=dict(record.graph_state or {}),
        final_output=dict(record.final_output or {}),
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def _build_graph_event_response(record: AgentGraphEventRecord) -> AgentGraphEventResponse:
    return AgentGraphEventResponse(
        event_id=record.event_id,
        run_id=record.run_id,
        traveller_id=record.traveller_id,
        trip_id=record.trip_id,
        event_type=record.event_type,
        node_name=record.node_name,
        sequence_number=record.sequence_number,
        payload=dict(record.payload or {}),
        created_at=record.created_at,
    )


def _get_saved_trip_or_raise(db: Session, trip_id: str) -> SavedTripRecord:
    record = db.query(SavedTripRecord).filter(SavedTripRecord.trip_id == trip_id).first()
    if record is None:
        raise ValueError(f"Saved trip not found for trip_id={trip_id}")
    return record


def _get_live_context_record(db: Session, trip_id: str) -> ActiveTripContextRecord | None:
    return db.query(ActiveTripContextRecord).filter(ActiveTripContextRecord.trip_id == trip_id).first()


def _get_graph_run_or_raise(db: Session, run_id: str) -> AgentGraphRunRecord:
    record = db.query(AgentGraphRunRecord).filter(AgentGraphRunRecord.run_id == run_id).first()
    if record is None:
        raise ValueError(f"Graph run not found for run_id={run_id}")
    return record


def _next_event_sequence(db: Session, run_id: str) -> int:
    current = (
        db.query(func.max(AgentGraphEventRecord.sequence_number))
        .filter(AgentGraphEventRecord.run_id == run_id)
        .scalar()
    )
    return int(current or 0) + 1


def _record_graph_event(
    db: Session,
    *,
    run_id: str,
    traveller_id: str,
    trip_id: str,
    event_type: str,
    node_name: str | None,
    payload: dict[str, Any],
) -> None:
    event = AgentGraphEventRecord(
        event_id=f"graph_event_{uuid4().hex}",
        run_id=run_id,
        traveller_id=traveller_id,
        trip_id=trip_id,
        event_type=event_type,
        node_name=node_name,
        sequence_number=_next_event_sequence(db, run_id),
        payload=_json_safe(payload),
    )
    db.add(event)
    db.commit()


def upsert_live_trip_context(
    db: Session,
    payload: LiveTripContextUpsertRequest,
) -> LiveTripContextResponse:
    _get_saved_trip_or_raise(db, payload.trip_id)

    record = _get_live_context_record(db, payload.trip_id)
    if record is None:
        record = ActiveTripContextRecord(
            trip_id=payload.trip_id,
            traveller_id=payload.traveller_id,
            planning_session_id=payload.planning_session_id,
            source_surface=payload.source_surface,
            trip_status=payload.trip_status,
            intent_hint=payload.intent_hint,
            transport_mode=payload.transport_mode,
            budget_level_override=payload.budget_level_override,
            available_minutes=payload.available_minutes,
            current_day_number=payload.current_day_number,
            current_slot_type=payload.current_slot_type,
            latitude=payload.gps.latitude if payload.gps else None,
            longitude=payload.gps.longitude if payload.gps else None,
            accuracy_meters=payload.gps.accuracy_meters if payload.gps else None,
            local_time_iso=payload.local_time_iso,
            timezone=payload.timezone,
            current_place_name=payload.current_place_name,
            current_city=payload.current_city,
            current_country=payload.current_country,
            context_payload=dict(payload.context_payload or {}),
        )
        db.add(record)
    else:
        record.traveller_id = payload.traveller_id
        record.planning_session_id = payload.planning_session_id
        record.source_surface = payload.source_surface
        record.trip_status = payload.trip_status
        record.intent_hint = payload.intent_hint
        record.transport_mode = payload.transport_mode
        record.budget_level_override = payload.budget_level_override
        record.available_minutes = payload.available_minutes
        record.current_day_number = payload.current_day_number
        record.current_slot_type = payload.current_slot_type
        if payload.gps is not None:
            record.latitude = payload.gps.latitude
            record.longitude = payload.gps.longitude
            record.accuracy_meters = payload.gps.accuracy_meters
        record.local_time_iso = payload.local_time_iso
        record.timezone = payload.timezone
        record.current_place_name = payload.current_place_name
        record.current_city = payload.current_city
        record.current_country = payload.current_country
        record.context_payload = dict(payload.context_payload or {})

    db.commit()
    db.refresh(record)
    return _build_live_context_response(record)


def get_live_trip_context(
    db: Session,
    trip_id: str,
) -> LiveTripContextResponse:
    record = _get_live_context_record(db, trip_id)
    if record is None:
        raise ValueError(f"Active live context not found for trip_id={trip_id}")
    return _build_live_context_response(record)


def write_live_action_to_memory(
    db: Session,
    payload: LiveActionWriteRequest,
) -> LiveActionWriteResponse:
    saved_trip = _get_saved_trip_or_raise(db, payload.trip_id)

    signal_record = TripSignalRecord(
        signal_id=f"signal_{uuid4().hex}",
        trip_id=payload.trip_id,
        traveller_id=payload.traveller_id,
        planning_session_id=payload.planning_session_id or saved_trip.planning_session_id,
        signal_type=payload.action_type,
        location_id=payload.location_id,
        day_number=payload.day_number,
        slot_type=payload.slot_type,
        payload=dict(payload.payload or {}),
    )

    if payload.action_type in {"nearby_selected", "gem_saved", "gem_accepted"}:
        saved_trip.selected_places_count = int(saved_trip.selected_places_count or 0) + 1
    elif payload.action_type in {
        "nearby_rejected",
        "place_closed",
        "place_unavailable",
        "gem_skipped",
    }:
        saved_trip.skipped_recommendations_count = int(saved_trip.skipped_recommendations_count or 0) + 1

    memory_event_type = f"live_{payload.action_type}"
    memory_record = TravellerMemoryRecord(
        traveller_id=payload.traveller_id,
        event_type=memory_event_type,
        source_surface=payload.source_surface,
        payload={
            "trip_id": payload.trip_id,
            "planning_session_id": payload.planning_session_id or saved_trip.planning_session_id,
            "location_id": payload.location_id,
            "day_number": payload.day_number,
            "slot_type": payload.slot_type,
            **dict(payload.payload or {}),
        },
    )

    db.add(saved_trip)
    db.add(signal_record)
    db.add(memory_record)
    db.commit()

    return LiveActionWriteResponse(
        signal_id=signal_record.signal_id,
        trip_id=payload.trip_id,
        traveller_id=payload.traveller_id,
        action_type=payload.action_type,
        memory_event_type=memory_event_type,
        saved=True,
    )


def _serialize_saved_trip(record: SavedTripRecord) -> dict[str, Any]:
    return {
        "trip_id": record.trip_id,
        "traveller_id": record.traveller_id,
        "planning_session_id": record.planning_session_id,
        "title": record.title,
        "destination": record.destination,
        "status": record.status,
        "source_surface": record.source_surface,
        "current_version_number": record.current_version_number,
        "current_version_id": record.current_version_id,
        "history_branch_label": record.history_branch_label,
        "parsed_constraints": dict(record.current_parsed_constraints or {}),
        "candidate_places": list(record.current_candidate_places or []),
        "itinerary_skeleton": list(record.current_itinerary_skeleton or []),
        "comparison_context": dict(record.comparison_context or {}),
        "selected_places_count": record.selected_places_count,
        "skipped_recommendations_count": record.skipped_recommendations_count,
        "replaced_slots_count": record.replaced_slots_count,
    }


def _serialize_signal(record: TripSignalRecord) -> dict[str, Any]:
    return {
        "signal_id": record.signal_id,
        "signal_type": record.signal_type,
        "location_id": record.location_id,
        "day_number": record.day_number,
        "slot_type": record.slot_type,
        "payload": dict(record.payload or {}),
        "created_at": record.created_at.isoformat(),
    }


def _serialize_memory(record: TravellerMemoryRecord) -> dict[str, Any]:
    return {
        "event_type": record.event_type,
        "source_surface": record.source_surface,
        "payload": dict(record.payload or {}),
        "created_at": record.created_at.isoformat(),
    }


def _load_recent_trip_signals(db: Session, trip_id: str, limit: int = 20) -> list[dict[str, Any]]:
    records = (
        db.query(TripSignalRecord)
        .filter(TripSignalRecord.trip_id == trip_id)
        .order_by(desc(TripSignalRecord.created_at), desc(TripSignalRecord.id))
        .limit(limit)
        .all()
    )
    return [_serialize_signal(record) for record in records]


def _load_recent_trip_memories(
    db: Session,
    traveller_id: str,
    trip_id: str,
    planning_session_id: str | None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    records = (
        db.query(TravellerMemoryRecord)
        .filter(TravellerMemoryRecord.traveller_id == traveller_id)
        .order_by(desc(TravellerMemoryRecord.created_at), desc(TravellerMemoryRecord.id))
        .limit(200)
        .all()
    )

    filtered: list[dict[str, Any]] = []
    for record in records:
        payload = dict(record.payload or {})
        if payload.get("trip_id") == trip_id:
            filtered.append(_serialize_memory(record))
            continue
        if planning_session_id and payload.get("planning_session_id") == planning_session_id:
            filtered.append(_serialize_memory(record))

    return filtered[:limit]


def _get_current_day_slot(saved_trip: dict[str, Any], live_context: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    day_number = live_context.get("current_day_number")
    slot_type = live_context.get("current_slot_type")
    if not day_number or not slot_type:
        return None, None

    itinerary = list(saved_trip.get("itinerary_skeleton") or [])
    for day in itinerary:
        if day.get("day_number") != day_number:
            continue
        for slot in list(day.get("slots") or []):
            if slot.get("slot_type") == slot_type:
                return day, slot
        return day, None

    return None, None


def _excluded_location_ids(recent_signals: list[dict[str, Any]]) -> set[str]:
    blocked_types = {
        "skipped_recommendation",
        "nearby_rejected",
        "place_closed",
        "place_unavailable",
    }
    blocked: set[str] = set()
    for signal in recent_signals:
        if signal.get("signal_type") in blocked_types and signal.get("location_id"):
            blocked.add(str(signal["location_id"]))
    return blocked


def _dedupe_locations(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item in items:
        location_id = str(item.get("location_id") or "")
        if not location_id or location_id in seen:
            continue
        seen.add(location_id)
        deduped.append(item)

    return deduped

def _text_contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _build_gem_embedding_text(
    saved_trip: dict[str, Any],
    item: dict[str, Any],
    live_context: dict[str, Any],
) -> str:
    parsed_constraints = dict(saved_trip.get("parsed_constraints") or {})
    interests = list(parsed_constraints.get("interests") or [])
    interests_text = ", ".join(interests) if interests else "general exploration"

    return (
        f"destination={saved_trip.get('destination') or parsed_constraints.get('destination') or 'unknown'}; "
        f"name={item.get('name') or 'unknown'}; "
        f"city={item.get('city') or 'unknown'}; "
        f"country={item.get('country') or 'unknown'}; "
        f"category={item.get('category') or 'unknown'}; "
        f"interests={interests_text}; "
        f"rating={item.get('rating') or 0}; "
        f"review_count={item.get('review_count') or 0}; "
        f"review_summary={item.get('review_summary') or item.get('why_alternative') or item.get('why_selected') or 'none'}; "
        f"intent_hint={live_context.get('intent_hint') or 'none'}; "
        f"current_slot_type={live_context.get('current_slot_type') or 'none'}"
    )


def _hidden_gem_interest_fit_bonus(item: dict[str, Any], saved_trip: dict[str, Any], live_context: dict[str, Any]) -> tuple[float, list[str]]:
    parsed_constraints = dict(saved_trip.get("parsed_constraints") or {})
    interests = list(parsed_constraints.get("interests") or [])
    text_blob = " ".join(
        [
            str(item.get("name") or ""),
            str(item.get("category") or ""),
            str(item.get("why_selected") or ""),
            str(item.get("why_alternative") or ""),
            str(item.get("review_summary") or ""),
        ]
    ).lower()

    score = 0.0
    reasons: list[str] = []

    mapping: dict[str, list[str]] = {
        "food": ["food", "dining", "restaurant", "market", "cuisine", "brunch"],
        "culture": ["culture", "heritage", "temple", "museum", "history", "shrine"],
        "nature": ["nature", "park", "garden", "river", "scenic", "bamboo"],
        "nightlife": ["nightlife", "bar", "club", "music", "late night"],
        "wellness": ["spa", "retreat", "onsen", "wellness", "calm"],
        "luxury": ["luxury", "upscale", "boutique", "fine dining"],
        "adventure": ["hike", "trail", "outdoor", "adventure", "kayak", "surf"],
    }

    for interest in interests[:3]:
        terms = mapping.get(str(interest), [])
        if _text_contains_any(text_blob, terms):
            score += 5.0
            reasons.append(f"matches your {interest} preference")

    intent_hint = str(live_context.get("intent_hint") or "").strip().lower()
    if intent_hint and intent_hint in text_blob:
        score += 4.0
        reasons.append(f"fits your live intent around {intent_hint}")

    slot_type = str(live_context.get("current_slot_type") or "").strip().lower()
    if slot_type == "lunch" and _text_contains_any(text_blob, ["food", "restaurant", "market", "cuisine"]):
        score += 3.0
        reasons.append("works well for your current lunch context")
    elif slot_type == "evening" and _text_contains_any(text_blob, ["bar", "nightlife", "lanes", "ambience", "atmosphere"]):
        score += 3.0
        reasons.append("fits your current evening context")
    elif slot_type == "morning" and _text_contains_any(text_blob, ["walkable", "culture", "temple", "garden", "calm"]):
        score += 2.5
        reasons.append("fits a lighter morning slot")

    return score, reasons


def _hidden_gem_route_fit_bonus(item: dict[str, Any], state: LiveGraphState) -> tuple[float, list[str]]:
    saved_trip = dict(state.get("saved_trip") or {})
    live_context = dict(state.get("live_context") or {})
    day, slot = _get_current_day_slot(saved_trip, live_context)

    score = 0.0
    reasons: list[str] = []

    if slot and str(item.get("location_id") or "") in set(slot.get("fallback_candidate_ids") or []):
        score += 6.0
        reasons.append("already fits this itinerary slot as a fallback")

    if day and day.get("geo_cluster") and item.get("geo_cluster") == day.get("geo_cluster"):
        score += 4.0
        reasons.append("stays coherent with your current day cluster")

    if slot and str(item.get("source_location_id") or "") == str(slot.get("assigned_location_id") or ""):
        score += 3.0
        reasons.append("is closely related to your active slot anchor")

    return score, reasons


def _hidden_gem_signal_bonus(item: dict[str, Any], recent_signals: list[dict[str, Any]]) -> tuple[float, list[str]]:
    blocked_ids = _excluded_location_ids(recent_signals)
    location_id = str(item.get("location_id") or "")

    if location_id in blocked_ids:
        return -1000.0, ["recently rejected or blocked"]

    return 0.0, []


def _hidden_gem_saturation_bonus(
    review_count: int,
    median_review_count: float,
) -> tuple[float, list[str]]:
    reasons: list[str] = []

    if review_count <= 0:
        return 2.0, ["has low visibility in the current pool"]

    ratio = review_count / max(median_review_count, 1.0)

    if ratio <= 0.35:
        return 10.0, ["looks meaningfully less saturated than the main trip pool"]
    if ratio <= 0.6:
        return 7.0, ["looks less saturated than the main trip pool"]
    if ratio <= 0.85:
        return 4.0, ["still feels a bit more under-the-radar than the main pool"]
    if ratio <= 1.15:
        return 1.0, ["has balanced visibility inside the current pool"]

    return -3.0, ["is becoming relatively well-known inside the current pool"]


def _build_hidden_gem_explanation(
    item: dict[str, Any],
    reasons: list[str],
) -> str:
    trimmed = reasons[:3]
    if trimmed:
        return (
            f"{item.get('name') or 'This place'} stands out as a hidden-gem candidate because it "
            f"{'; '.join(trimmed)}."
        )

    return (
        f"{item.get('name') or 'This place'} looks like a strong underrated option based on fit, "
        f"quality, and lower saturation inside your current trip pool."
    )


def _nearby_candidates_from_state(state: LiveGraphState) -> list[dict[str, Any]]:
    saved_trip = dict(state.get("saved_trip") or {})
    live_context = dict(state.get("live_context") or {})
    recent_signals = list(state.get("recent_signals") or [])

    excluded_ids = _excluded_location_ids(recent_signals)
    day, slot = _get_current_day_slot(saved_trip, live_context)

    slot_alternatives = list(slot.get("alternatives") or []) if slot else []
    slot_fallback_ids = set(slot.get("fallback_candidate_ids") or []) if slot else set()
    candidate_places = list(saved_trip.get("candidate_places") or [])

    merged = _dedupe_locations(slot_alternatives + candidate_places)
    scored: list[dict[str, Any]] = []

    for item in merged:
        location_id = str(item.get("location_id") or "")
        if location_id in excluded_ids:
            continue

        score = float(item.get("score") or 0.0)
        reason_bits: list[str] = []

        if location_id in slot_fallback_ids:
            score += 8.0
            reason_bits.append("already fits this part of the itinerary")

        if slot and location_id == slot.get("assigned_location_id"):
            score += 10.0
            reason_bits.append("currently aligned with your active slot")

        if live_context.get("intent_hint"):
            hint = str(live_context["intent_hint"]).lower()
            text_blob = " ".join(
                [
                    str(item.get("name") or ""),
                    str(item.get("category") or ""),
                    str(item.get("why_alternative") or ""),
                    str(item.get("why_selected") or ""),
                ]
            ).lower()
            if hint in text_blob:
                score += 4.0
                reason_bits.append(f"matches your live intent hint: {hint}")

        scored.append(
            {
                **item,
                "live_score": round(score, 1),
                "live_reason": "; ".join(reason_bits) if reason_bits else "strong live-fit candidate from your saved trip context",
            }
        )

    scored.sort(key=lambda item: float(item.get("live_score") or 0.0), reverse=True)
    return scored[:_MAX_NEARBY_RESULTS]


def _gem_candidates_from_state(db: Session, state: LiveGraphState) -> list[dict[str, Any]]:
    saved_trip = dict(state.get("saved_trip") or {})
    live_context = dict(state.get("live_context") or {})
    recent_signals = list(state.get("recent_signals") or [])

    parsed_constraints = dict(saved_trip.get("parsed_constraints") or {})
    candidate_places = list(saved_trip.get("candidate_places") or [])
    day, slot = _get_current_day_slot(saved_trip, live_context)

    expanded: list[dict[str, Any]] = []

    for candidate in candidate_places:
        expanded.append(candidate)

        for related in list(candidate.get("related_locations") or []):
            expanded.append(
                {
                    **related,
                    "rating": candidate.get("rating", 4.5),
                    "review_count": max(int(candidate.get("review_count") or 0) // 2, 50),
                    "review_authenticity": candidate.get("review_authenticity"),
                    "review_summary": candidate.get("review_summary"),
                    "why_selected": candidate.get("why_selected"),
                }
            )

    if slot:
        for alternative in list(slot.get("alternatives") or []):
            expanded.append(
                {
                    **alternative,
                    "rating": 4.5,
                    "review_count": 150,
                    "review_authenticity": "medium",
                    "review_summary": alternative.get("why_alternative"),
                }
            )

    deduped = _dedupe_locations(expanded)

    review_counts = [
        int(item.get("review_count") or 0)
        for item in deduped
        if int(item.get("review_count") or 0) > 0
    ]
    median_review_count = median(review_counts) if review_counts else 1000.0

    gems: list[dict[str, Any]] = []
    traveller_id = str(state.get("traveller_id") or "")

    for item in deduped:
        signal_penalty, signal_reasons = _hidden_gem_signal_bonus(item, recent_signals)
        if signal_penalty <= -1000.0:
            continue

        rating = float(item.get("rating") or 0.0)
        review_count = int(item.get("review_count") or 0)
        base_score = float(item.get("score") or item.get("live_score") or 0.0)

        quality_score = rating * 10.0
        baseline_fit = min(base_score / 4.0, 18.0)

        interest_bonus, interest_reasons = _hidden_gem_interest_fit_bonus(item, saved_trip, live_context)
        route_bonus, route_reasons = _hidden_gem_route_fit_bonus(item, state)
        saturation_bonus, saturation_reasons = _hidden_gem_saturation_bonus(review_count, median_review_count)

        authenticity_bonus = 0.0
        authenticity = item.get("review_authenticity")
        if authenticity == "high":
            authenticity_bonus = 2.0
        elif authenticity == "medium":
            authenticity_bonus = 1.0

        persona_relevance_score: float | None = None
        if traveller_id:
            persona_relevance_score = calculate_persona_relevance_score(
                db=db,
                traveller_id=traveller_id,
                text=_build_gem_embedding_text(saved_trip, item, live_context),
            )

        persona_bonus = (persona_relevance_score or 0.0) * 14.0

        gem_score = (
            quality_score
            + baseline_fit
            + interest_bonus
            + route_bonus
            + saturation_bonus
            + authenticity_bonus
            + persona_bonus
            + signal_penalty
        )

        explanation_reasons = (
            interest_reasons
            + route_reasons
            + saturation_reasons
            + signal_reasons
        )
        if persona_relevance_score is not None and persona_relevance_score >= 0.72:
            explanation_reasons.append("shows a strong persona fit for this traveller")

        gems.append(
            {
                **item,
                "gem_score": round(gem_score, 1),
                "persona_relevance_score": round(persona_relevance_score or 0.0, 4),
                "gem_reason": _build_hidden_gem_explanation(item, explanation_reasons),
                "fit_reasons": explanation_reasons[:4],
                "source_context": (
                    "itinerary_slot"
                    if slot and str(item.get("location_id") or "") in set(slot.get("fallback_candidate_ids") or [])
                    else "destination_pool"
                ),
                "underrated_signal": review_count < median_review_count,
                "current_day_number": live_context.get("current_day_number"),
                "current_slot_type": live_context.get("current_slot_type"),
                "traveller_interests": list(parsed_constraints.get("interests") or []),
            }
        )

    gems.sort(key=lambda item: float(item.get("gem_score") or 0.0), reverse=True)
    return gems[:_MAX_GEM_RESULTS]


def _build_alerts_from_state(state: LiveGraphState) -> list[dict[str, Any]]:
    live_context = dict(state.get("live_context") or {})
    recent_signals = list(state.get("recent_signals") or [])
    saved_trip = dict(state.get("saved_trip") or {})
    _, slot = _get_current_day_slot(saved_trip, live_context)

    alerts: list[dict[str, Any]] = []

    for signal in recent_signals[:5]:
        signal_type = signal.get("signal_type")
        if signal_type in {"place_closed", "place_unavailable"}:
            alerts.append(
                {
                    "severity": "high",
                    "title": f"{signal_type.replace('_', ' ').title()} detected",
                    "message": f"Recent live feedback suggests a place in your active flow may no longer be usable.",
                    "location_id": signal.get("location_id"),
                }
            )

    available_minutes = live_context.get("available_minutes")
    if isinstance(available_minutes, int) and available_minutes < 45:
        alerts.append(
            {
                "severity": "medium",
                "title": "Tight time window",
                "message": f"You currently have only about {available_minutes} minutes available, so a lighter nearby option may be better.",
            }
        )

    if not live_context.get("latitude") or not live_context.get("longitude"):
        alerts.append(
            {
                "severity": "low",
                "title": "GPS precision missing",
                "message": "Nearby ranking is running without exact live coordinates, so distance quality is approximate for now.",
            }
        )

    if slot and list(slot.get("alternatives") or []):
        alerts.append(
            {
                "severity": "low",
                "title": "Alternatives ready",
                "message": "Your active slot already has fallback alternatives available if you want a quick swap.",
            }
        )

    return alerts[:5]


def _latest_live_blocker_signal(state: LiveGraphState) -> dict[str, Any] | None:
    for signal in list(state.get("recent_signals") or []):
        if signal.get("signal_type") in {"place_closed", "place_unavailable", "nearby_rejected"}:
            return signal
    return None


def _build_replan_alternatives(state: LiveGraphState) -> list[dict[str, Any]]:
    saved_trip = dict(state.get("saved_trip") or {})
    live_context = dict(state.get("live_context") or {})
    blocker = _latest_live_blocker_signal(state)
    blocked_location_id = blocker.get("location_id") if blocker else None

    _, slot = _get_current_day_slot(saved_trip, live_context)
    alternatives = list(slot.get("alternatives") or []) if slot else []
    nearby_candidates = _nearby_candidates_from_state(state)

    merged = _dedupe_locations(alternatives + nearby_candidates)
    filtered = [
        item
        for item in merged
        if str(item.get("location_id") or "") != str(blocked_location_id or "")
    ]

    return filtered[:_MAX_NEARBY_RESULTS]

def _signal_location_ids_by_type(
    recent_signals: list[dict[str, Any]],
    signal_types: set[str],
) -> list[str]:
    ids: list[str] = []
    for signal in recent_signals:
        if signal.get("signal_type") in signal_types and signal.get("location_id"):
            ids.append(str(signal["location_id"]))
    return ids


def _build_nearby_request_from_state(
    state: LiveGraphState,
    *,
    query: str,
    open_now_only: bool = False,
    extra_blocked_ids: set[str] | None = None,
) -> NearbyDiscoveryRequest:
    saved_trip = dict(state.get("saved_trip") or {})
    live_context = dict(state.get("live_context") or {})
    recent_signals = list(state.get("recent_signals") or [])

    parsed_constraints = dict(saved_trip.get("parsed_constraints") or {})
    blocked_ids = set(_excluded_location_ids(recent_signals))
    blocked_ids.update(extra_blocked_ids or set())

    return NearbyDiscoveryRequest(
        latitude=float(live_context.get("latitude") or 0.0),
        longitude=float(live_context.get("longitude") or 0.0),
        city=live_context.get("current_city") or saved_trip.get("destination"),
        country=live_context.get("current_country"),
        query=query,
        traveller_id=str(state.get("traveller_id") or "") or None,
        traveller_type=parsed_constraints.get("group_type"),
        interests=list(parsed_constraints.get("interests") or []),
        budget=str(
            live_context.get("budget_level_override")
            or parsed_constraints.get("budget")
            or "midrange"
        ),
        limit=_MAX_NEARBY_RESULTS,
        starting_radius_meters=800 if live_context.get("transport_mode") in {None, "walk"} else 1500,
        max_radius_meters=3000 if live_context.get("transport_mode") in {None, "walk"} else 5000,
        adaptive_radius=True,
        source_surface="live_runtime",
        context=NearbyDiscoveryContext(
            traveller_id=str(state.get("traveller_id") or "") or None,
            trip_id=str(state.get("trip_id") or "") or None,
            planning_session_id=state.get("planning_session_id"),
            intent_hint=live_context.get("intent_hint"),
            transport_mode=str(live_context.get("transport_mode") or "walk"),
            budget=str(
                live_context.get("budget_level_override")
                or parsed_constraints.get("budget")
                or "midrange"
            ),
            current_day_number=live_context.get("current_day_number"),
            current_slot_type=live_context.get("current_slot_type"),
            available_minutes=live_context.get("available_minutes"),
            current_place_name=live_context.get("current_place_name"),
            current_city=live_context.get("current_city"),
            current_country=live_context.get("current_country"),
            open_now_only=open_now_only,
            exclude_location_ids=sorted(blocked_ids),
            rejected_location_ids=_signal_location_ids_by_type(
                recent_signals,
                {"nearby_rejected", "gem_skipped"},
            ),
            closed_location_ids=_signal_location_ids_by_type(
                recent_signals,
                {"place_closed"},
            ),
            unavailable_location_ids=_signal_location_ids_by_type(
                recent_signals,
                {"place_unavailable"},
            ),
            context_payload={
                "saved_trip": saved_trip,
                "recent_signals": recent_signals,
            },
        ),
    )


def _infer_supervisor_route(message: str, state: LiveGraphState) -> tuple[str, str]:
    lowered = message.lower()

    if re.search(r"\b(monitor|monitoring|check my plan|check the plan|active itinerary|watch for issues|proactive)\b", lowered):
        return "proactive_monitor_agent", "Detected proactive itinerary monitoring intent."

    if re.search(r"\b(hidden gem|underrated|offbeat|local spot|gem)\b", lowered):
        return "gem_agent", "Detected hidden-gem or underrated-place intent."

    if re.search(r"\b(closed|unavailable|not available|reject|rejected|another option|alternative)\b", lowered):
        return "live_replan_agent", "Detected live disruption or replacement intent."

    if re.search(r"\b(alert|anything changed|conflict|timing issue|issue)\b", lowered):
        return "alert_agent", "Detected active-trip alert or itinerary-health-check intent."

    live_context = dict(state.get("live_context") or {})
    if live_context.get("latitude") is not None and live_context.get("longitude") is not None:
        return "nearby_agent", "Detected active live context with coordinates, defaulting to nearby live assistance."

    if re.search(r"\b(nearby|near me|around me|right now|walking distance|open now)\b", lowered):
        return "nearby_agent", "Detected nearby/on-ground discovery intent."

    return "nearby_agent", "Defaulted to nearby live assistance for active-trip handling."


def _bootstrap_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    saved_trip_record = _get_saved_trip_or_raise(db, state["trip_id"])
    live_context_record = _get_live_context_record(db, state["trip_id"])

    saved_trip = _serialize_saved_trip(saved_trip_record)
    persisted_live_context = (
        _build_live_context_response(live_context_record).model_dump(mode="json")
        if live_context_record is not None
        else {}
    )
    request_live_context = dict(state.get("live_context") or {})
    live_context = _merge_live_context_dicts(
        persisted_live_context,
        request_live_context,
    )
    recent_signals = _load_recent_trip_signals(db, state["trip_id"], limit=20)
    recent_memories = _load_recent_trip_memories(
        db,
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        planning_session_id=state.get("planning_session_id"),
        limit=20,
    )

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="context_loaded",
        node_name="bootstrap",
        payload={
            "has_live_context": bool(live_context),
            "recent_signal_count": len(recent_signals),
            "recent_memory_count": len(recent_memories),
            "trip_status": saved_trip.get("status"),
        },
    )

    return {
        "saved_trip": saved_trip,
        "live_context": live_context,
        "recent_signals": recent_signals,
        "recent_memories": recent_memories,
    }


def _supervisor_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    routed_agent, rationale = _infer_supervisor_route(state["message"], state)
    supervisor = {
        "intent": routed_agent,
        "rationale": rationale,
        "evaluated_at": _now_iso(),
    }

    run_record = _get_graph_run_or_raise(db, state["run_id"])
    run_record.routed_agent = routed_agent
    run_record.supervisor_intent = routed_agent
    run_record.graph_state = {
        **dict(run_record.graph_state or {}),
        "supervisor": supervisor,
    }
    db.add(run_record)
    db.commit()

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="supervisor_routed",
        node_name="supervisor",
        payload=supervisor,
    )

    return {
        "supervisor": supervisor,
        "routed_agent": routed_agent,
    }


def _nearby_agent_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    live_context = dict(state.get("live_context") or {})

    if live_context.get("latitude") is None or live_context.get("longitude") is None:
        recommendations = _nearby_candidates_from_state(state)
        result = {
            "agent": "nearby_agent",
            "title": "Best live nearby-fit options",
            "message": "GPS was missing, so these options were ranked from your active trip context and itinerary pool only.",
            "recommendations": recommendations,
            "walking_alternatives": [],
            "fallbacks": [],
            "radius_used_meters": 0,
            "search_expansions": [],
            "blocked_location_ids": sorted(_excluded_location_ids(list(state.get("recent_signals") or []))),
        }
    else:
        nearby_request = _build_nearby_request_from_state(
            state,
            query=state["message"],
            open_now_only=False,
        )
        nearby_response = discover_context_aware_nearby_places(db, nearby_request)
        payload = nearby_response.model_dump(mode="json")

        result = {
            "agent": "nearby_agent",
            "title": "Best live nearby-fit options",
            "message": "These options were ranked using your live location, travel context, budget, persona fit, and active trip state.",
            **payload,
        }

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="agent_completed",
        node_name="nearby_agent",
        payload={"recommendation_count": len(result.get("recommendations") or [])},
    )

    return {"result": result}


def _gem_agent_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    gem_recommendations = _gem_candidates_from_state(db, state)

    result = {
        "agent": "gem_agent",
        "title": "Underrated places around your current trip",
        "message": "These recommendations tilt toward stronger fit with lighter crowd saturation inside your active trip pool.",
        "gems": gem_recommendations,
    }

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="agent_completed",
        node_name="gem_agent",
        payload={"gem_count": len(gem_recommendations)},
    )

    return {"result": result}


def _alert_agent_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    alerts = _build_alerts_from_state(state)

    result = {
        "agent": "alert_agent",
        "title": "Active-trip checks",
        "message": "Here are the current issues or watch-outs detected from your live trip context.",
        "alerts": alerts,
    }

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="agent_completed",
        node_name="alert_agent",
        payload={"alert_count": len(alerts)},
    )

    return {"result": result}


def _live_replan_agent_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    live_context = dict(state.get("live_context") or {})
    blocker = _latest_live_blocker_signal(state)
    blocked_location_id = str(blocker.get("location_id") or "") if blocker else ""

    if live_context.get("latitude") is None or live_context.get("longitude") is None:
        alternatives = _build_replan_alternatives(state)
        result = {
            "agent": "live_replan_agent",
            "title": "Best live alternatives",
            "message": "I filtered your current trip context and recent live blockers to surface the best next options, using itinerary context because exact GPS was missing.",
            "blocked_signal": blocker,
            "alternatives": alternatives,
            "walking_alternatives": [],
            "fallbacks": [],
            "radius_used_meters": 0,
            "search_expansions": [],
        }
    else:
        nearby_request = _build_nearby_request_from_state(
            state,
            query=state["message"],
            open_now_only=True,
            extra_blocked_ids={blocked_location_id} if blocked_location_id else set(),
        )
        nearby_response = discover_context_aware_nearby_places(db, nearby_request)

        alternatives = nearby_response.recommendations or nearby_response.fallbacks
        result = {
            "agent": "live_replan_agent",
            "title": "Best live alternatives",
            "message": "I re-ranked nearby options with stronger weight on walkability, live availability, and your current trip context.",
            "blocked_signal": blocker,
            "alternatives": [item.model_dump(mode="json") for item in alternatives],
            "walking_alternatives": [item.model_dump(mode="json") for item in nearby_response.walking_alternatives],
            "fallbacks": [item.model_dump(mode="json") for item in nearby_response.fallbacks],
            "radius_used_meters": nearby_response.radius_used_meters,
            "search_expansions": nearby_response.search_expansions,
            "blocked_location_ids": nearby_response.blocked_location_ids,
        }

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="agent_completed",
        node_name="live_replan_agent",
        payload={"alternative_count": len(result.get("alternatives") or [])},
    )

    return {"result": result}

def _proactive_monitor_agent_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    inspect_response = inspect_active_trip_alerts(
        db,
        ProactiveMonitorInspectRequest(
            traveller_id=state["traveller_id"],
            trip_id=state["trip_id"],
            planning_session_id=state.get("planning_session_id"),
            source_surface="live_runtime_graph",
            current_day_only=False,
            max_days_to_check=2,
        ),
    )

    alerts = [item.model_dump(mode="json") for item in inspect_response.alerts]

    result = {
        "agent": "proactive_monitor_agent",
        "title": "Active itinerary monitoring",
        "message": "I inspected the active itinerary for closure, quality, timing, and fallback risks before the traveller manually encounters them.",
        "alerts": alerts,
        "generated_count": inspect_response.generated_count,
        "open_alert_count": inspect_response.open_alert_count,
        "checked_at": inspect_response.checked_at.isoformat(),
    }

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="agent_completed",
        node_name="proactive_monitor_agent",
        payload={
            "generated_count": inspect_response.generated_count,
            "open_alert_count": inspect_response.open_alert_count,
        },
    )

    return {
        "proactive_alerts": alerts,
        "result": result,
    }

def _finalize_node(db: Session, state: LiveGraphState) -> LiveGraphState:
    run_record = _get_graph_run_or_raise(db, state["run_id"])
    run_record.status = "completed"
    run_record.routed_agent = state.get("routed_agent")
    run_record.supervisor_intent = dict(state.get("supervisor") or {}).get("intent")
    run_record.graph_state = _json_safe(dict(state))
    run_record.final_output = _json_safe(dict(state.get("result") or {}))

    db.add(run_record)
    db.commit()

    _record_graph_event(
        db,
        run_id=state["run_id"],
        traveller_id=state["traveller_id"],
        trip_id=state["trip_id"],
        event_type="run_finalized",
        node_name="finalize",
        payload={
            "status": run_record.status,
            "routed_agent": run_record.routed_agent,
        },
    )

    return {}


def _route_from_supervisor(state: LiveGraphState) -> str:
    return str(state.get("routed_agent") or "nearby_agent")


def _build_graph(db: Session):
    graph = StateGraph(LiveGraphState)

    graph.add_node("bootstrap", lambda state: _bootstrap_node(db, state))
    graph.add_node("supervisor", lambda state: _supervisor_node(db, state))
    graph.add_node("nearby_agent", lambda state: _nearby_agent_node(db, state))
    graph.add_node("gem_agent", lambda state: _gem_agent_node(db, state))
    graph.add_node("alert_agent", lambda state: _alert_agent_node(db, state))
    graph.add_node("proactive_monitor_agent", lambda state: _proactive_monitor_agent_node(db, state))
    graph.add_node("live_replan_agent", lambda state: _live_replan_agent_node(db, state))
    graph.add_node("finalize", lambda state: _finalize_node(db, state))

    graph.add_edge(START, "bootstrap")
    graph.add_edge("bootstrap", "supervisor")
    graph.add_conditional_edges(
        "supervisor",
        _route_from_supervisor,
        {
            "nearby_agent": "nearby_agent",
            "gem_agent": "gem_agent",
            "alert_agent": "alert_agent",
            "proactive_monitor_agent": "proactive_monitor_agent",
            "live_replan_agent": "live_replan_agent",
        },
    )
    graph.add_edge("nearby_agent", "finalize")
    graph.add_edge("gem_agent", "finalize")
    graph.add_edge("alert_agent", "finalize")
    graph.add_edge("proactive_monitor_agent", "finalize")
    graph.add_edge("live_replan_agent", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile(checkpointer=_CHECKPOINTER)


def _create_graph_run_record(
    db: Session,
    payload: LiveRuntimeOrchestrateRequest,
) -> AgentGraphRunRecord:
    _get_saved_trip_or_raise(db, payload.trip_id)

    run_record = AgentGraphRunRecord(
        run_id=f"live_run_{uuid4().hex}",
        traveller_id=payload.traveller_id,
        trip_id=payload.trip_id,
        planning_session_id=payload.planning_session_id,
        source_surface=payload.source_surface,
        user_message=payload.message,
        status="running",
        routed_agent=None,
        supervisor_intent=None,
        checkpoint_thread_id=f"trip::{payload.trip_id}",
        graph_state={},
        final_output={},
    )
    db.add(run_record)
    db.commit()
    db.refresh(run_record)
    return run_record


def _apply_context_patch_if_present(
    db: Session,
    payload: LiveRuntimeOrchestrateRequest,
) -> LiveTripContextResponse | None:
    if payload.context_patch is None:
        existing = _get_live_context_record(db, payload.trip_id)
        return _build_live_context_response(existing) if existing is not None else None

    existing = _get_live_context_record(db, payload.trip_id)
    request = LiveTripContextUpsertRequest(
        traveller_id=payload.traveller_id,
        trip_id=payload.trip_id,
        planning_session_id=payload.planning_session_id or (existing.planning_session_id if existing else None),
        source_surface=payload.source_surface,
        trip_status=payload.context_patch.trip_status or (existing.trip_status if existing else "active"),
        intent_hint=payload.context_patch.intent_hint if payload.context_patch.intent_hint is not None else (existing.intent_hint if existing else None),
        transport_mode=payload.context_patch.transport_mode if payload.context_patch.transport_mode is not None else (existing.transport_mode if existing else None),
        budget_level_override=payload.context_patch.budget_level_override if payload.context_patch.budget_level_override is not None else (existing.budget_level_override if existing else None),
        available_minutes=payload.context_patch.available_minutes if payload.context_patch.available_minutes is not None else (existing.available_minutes if existing else None),
        current_day_number=payload.context_patch.current_day_number if payload.context_patch.current_day_number is not None else (existing.current_day_number if existing else None),
        current_slot_type=payload.context_patch.current_slot_type if payload.context_patch.current_slot_type is not None else (existing.current_slot_type if existing else None),
        gps=payload.context_patch.gps,
        local_time_iso=payload.context_patch.local_time_iso if payload.context_patch.local_time_iso is not None else (existing.local_time_iso if existing else None),
        timezone=payload.context_patch.timezone if payload.context_patch.timezone is not None else (existing.timezone if existing else None),
        current_place_name=payload.context_patch.current_place_name if payload.context_patch.current_place_name is not None else (existing.current_place_name if existing else None),
        current_city=payload.context_patch.current_city if payload.context_patch.current_city is not None else (existing.current_city if existing else None),
        current_country=payload.context_patch.current_country if payload.context_patch.current_country is not None else (existing.current_country if existing else None),
        context_payload=payload.context_patch.context_payload if payload.context_patch.context_payload is not None else (dict(existing.context_payload or {}) if existing else {}),
    )
    return upsert_live_trip_context(db, request)


def orchestrate_live_runtime(
    db: Session,
    payload: LiveRuntimeOrchestrateRequest,
) -> LiveRuntimeOrchestrateResponse:
    live_context = _apply_context_patch_if_present(db, payload)
    run_record = _create_graph_run_record(db, payload)

    try:
        graph = _build_graph(db)
        initial_state: LiveGraphState = {
            "run_id": run_record.run_id,
            "traveller_id": payload.traveller_id,
            "trip_id": payload.trip_id,
            "planning_session_id": payload.planning_session_id,
            "source_surface": payload.source_surface,
            "message": payload.message,
            "live_context": live_context.model_dump(mode="json") if live_context is not None else {},
        }

        graph.invoke(
            initial_state,
            config={"configurable": {"thread_id": run_record.checkpoint_thread_id}},
        )

        refreshed = _get_graph_run_or_raise(db, run_record.run_id)
        return LiveRuntimeOrchestrateResponse(
            run=_build_graph_run_response(refreshed),
            live_context=live_context,
        )
    except Exception as exc:
        failed = _get_graph_run_or_raise(db, run_record.run_id)
        failed.status = "failed"
        failed.graph_state = {
            **dict(failed.graph_state or {}),
            "error": str(exc),
        }
        db.add(failed)
        db.commit()

        _record_graph_event(
            db,
            run_id=run_record.run_id,
            traveller_id=payload.traveller_id,
            trip_id=payload.trip_id,
            event_type="run_failed",
            node_name="runtime",
            payload={"error": str(exc)},
        )
        raise


def stream_live_runtime(
    db: Session,
    payload: LiveRuntimeOrchestrateRequest,
) -> Generator[str, None, None]:
    live_context = _apply_context_patch_if_present(db, payload)
    run_record = _create_graph_run_record(db, payload)

    yield json.dumps(
        {
            "type": "meta",
            "run_id": run_record.run_id,
            "trip_id": payload.trip_id,
            "traveller_id": payload.traveller_id,
            "has_live_context": live_context is not None,
        }
    ) + "\n"

    try:
        graph = _build_graph(db)
        initial_state: LiveGraphState = {
            "run_id": run_record.run_id,
            "traveller_id": payload.traveller_id,
            "trip_id": payload.trip_id,
            "planning_session_id": payload.planning_session_id,
            "source_surface": payload.source_surface,
            "message": payload.message,
            "live_context": live_context.model_dump(mode="json") if live_context is not None else {},
        }

        for update in graph.stream(
            initial_state,
            config={"configurable": {"thread_id": run_record.checkpoint_thread_id}},
            stream_mode="updates",
        ):
            node_name, node_payload = next(iter(update.items()))
            yield json.dumps(
                {
                    "type": "graph_update",
                    "run_id": run_record.run_id,
                    "node_name": node_name,
                    "payload": _json_safe(node_payload),
                }
            ) + "\n"

        refreshed = _get_graph_run_or_raise(db, run_record.run_id)
        yield json.dumps(
            {
                "type": "final",
                "payload": LiveRuntimeOrchestrateResponse(
                    run=_build_graph_run_response(refreshed),
                    live_context=live_context,
                ).model_dump(mode="json"),
            }
        ) + "\n"
    except Exception as exc:
        failed = _get_graph_run_or_raise(db, run_record.run_id)
        failed.status = "failed"
        failed.graph_state = {
            **dict(failed.graph_state or {}),
            "error": str(exc),
        }
        db.add(failed)
        db.commit()

        _record_graph_event(
            db,
            run_id=run_record.run_id,
            traveller_id=payload.traveller_id,
            trip_id=payload.trip_id,
            event_type="run_failed",
            node_name="runtime",
            payload={"error": str(exc)},
        )

        yield json.dumps(
            {
                "type": "error",
                "run_id": run_record.run_id,
                "message": str(exc),
            }
        ) + "\n"


def get_graph_run(
    db: Session,
    run_id: str,
) -> AgentGraphRunResponse:
    record = _get_graph_run_or_raise(db, run_id)
    return _build_graph_run_response(record)


def list_graph_events(
    db: Session,
    run_id: str,
    limit: int = 200,
) -> AgentGraphEventListResponse:
    _get_graph_run_or_raise(db, run_id)

    records = (
        db.query(AgentGraphEventRecord)
        .filter(AgentGraphEventRecord.run_id == run_id)
        .order_by(AgentGraphEventRecord.sequence_number.asc(), AgentGraphEventRecord.id.asc())
        .limit(limit)
        .all()
    )

    return AgentGraphEventListResponse(
        run_id=run_id,
        total=len(records),
        items=[_build_graph_event_response(record) for record in records],
    )