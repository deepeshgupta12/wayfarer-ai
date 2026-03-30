import json
import re
from collections.abc import Generator

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.saved_trip import SavedTripRecord
from app.models.trip_plan import TripPlanRecord
from app.schemas.assistant import (
    AssistantIntentClassification,
    AssistantOrchestrateRequest,
    AssistantOrchestrateResponse,
)
from app.schemas.destination import DestinationComparisonRequest, DestinationGuideRequest
from app.schemas.live_runtime import LiveRuntimeOrchestrateRequest
from app.schemas.trip_plan import TripBriefParseRequest
from app.services.destination_service import (
    build_destination_guide,
    compare_destinations,
    stream_destination_guide,
)
from app.services.live_runtime_service import (
    orchestrate_live_runtime,
    stream_live_runtime,
)
from app.services.trip_plan_service import (
    DESTINATION_HINTS,
    _extract_duration_days,
    get_trip_plan_summary,
    parse_and_save_trip_brief,
)


_LIVE_RUNTIME_PATTERNS = [
    r"\bnear me\b",
    r"\bnearby\b",
    r"\bright now\b",
    r"\bopen now\b",
    r"\baround me\b",
    r"\bwalking distance\b",
    r"\bhidden gem\b",
    r"\bunderrated\b",
    r"\boffbeat\b",
    r"\bcheck my plan\b",
    r"\bmonitor\b",
    r"\bproactive\b",
    r"\balert\b",
    r"\bclosed\b",
    r"\bunavailable\b",
    r"\balternative\b",
    r"\breplace this place\b",
]

_EXISTING_CONTEXT_PATTERNS = [
    r"\bmy trip\b",
    r"\bmy itinerary\b",
    r"\bthis trip\b",
    r"\bthis itinerary\b",
    r"\bcurrent trip\b",
    r"\bactive trip\b",
    r"\bday\s+\d+\b",
    r"\breplace\b",
    r"\bswap\b",
    r"\bchange\b",
    r"\bslot\b",
    r"\bnear me\b",
    r"\bnearby\b",
    r"\bright now\b",
    r"\bmonitor\b",
    r"\balert\b",
    r"\bclosed\b",
    r"\bunavailable\b",
    r"\balternative\b",
]


def _extract_known_destinations(message: str) -> list[str]:
    lowered = message.lower()
    found: list[str] = []

    for destination in DESTINATION_HINTS:
        if destination in lowered and destination.title() not in found:
            found.append(destination.title())

    if len(found) >= 2:
        return found[:2]

    capitalized_matches = re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\b", message)
    for item in capitalized_matches:
        normalized = item.strip()
        if normalized not in found:
            found.append(normalized)
        if len(found) >= 2:
            break

    return found[:2]


def _looks_like_live_runtime_request(message: str) -> bool:
    lowered = message.lower().strip()
    return any(re.search(pattern, lowered) for pattern in _LIVE_RUNTIME_PATTERNS)


def _looks_like_existing_context_follow_up(message: str) -> bool:
    lowered = message.lower().strip()
    return any(re.search(pattern, lowered) for pattern in _EXISTING_CONTEXT_PATTERNS)


def _get_trip_by_id(db: Session, trip_id: str | None) -> SavedTripRecord | None:
    if not trip_id:
        return None
    return (
        db.query(SavedTripRecord)
        .filter(SavedTripRecord.trip_id == trip_id)
        .first()
    )


def _get_trip_by_planning_session(db: Session, planning_session_id: str | None) -> SavedTripRecord | None:
    if not planning_session_id:
        return None
    return (
        db.query(SavedTripRecord)
        .filter(SavedTripRecord.planning_session_id == planning_session_id)
        .order_by(desc(SavedTripRecord.updated_at), desc(SavedTripRecord.id))
        .first()
    )


def _get_plan_by_id(db: Session, planning_session_id: str | None) -> TripPlanRecord | None:
    if not planning_session_id:
        return None
    return (
        db.query(TripPlanRecord)
        .filter(TripPlanRecord.planning_session_id == planning_session_id)
        .first()
    )


def _get_latest_trip_for_traveller(db: Session, traveller_id: str | None) -> SavedTripRecord | None:
    if not traveller_id:
        return None
    return (
        db.query(SavedTripRecord)
        .filter(SavedTripRecord.traveller_id == traveller_id)
        .order_by(desc(SavedTripRecord.updated_at), desc(SavedTripRecord.id))
        .first()
    )


def _get_latest_plan_for_traveller(db: Session, traveller_id: str | None) -> TripPlanRecord | None:
    if not traveller_id:
        return None
    return (
        db.query(TripPlanRecord)
        .filter(TripPlanRecord.traveller_id == traveller_id)
        .order_by(desc(TripPlanRecord.updated_at), desc(TripPlanRecord.id))
        .first()
    )


def _resolve_assistant_context(
    db: Session,
    payload: AssistantOrchestrateRequest,
) -> dict[str, str | None]:
    traveller_id = payload.context.traveller_id
    planning_session_id = payload.context.planning_session_id
    trip_id = payload.context.trip_id
    message = payload.message

    resolved_trip = _get_trip_by_id(db, trip_id)
    if resolved_trip is not None:
        trip_id = resolved_trip.trip_id
        traveller_id = resolved_trip.traveller_id
        planning_session_id = planning_session_id or resolved_trip.planning_session_id

    resolved_plan = _get_plan_by_id(db, planning_session_id)
    if resolved_plan is not None:
        planning_session_id = resolved_plan.planning_session_id
        traveller_id = traveller_id or resolved_plan.traveller_id

        trip_from_plan = _get_trip_by_planning_session(db, resolved_plan.planning_session_id)
        if trip_from_plan is not None:
            trip_id = trip_from_plan.trip_id
            traveller_id = trip_from_plan.traveller_id
            planning_session_id = trip_from_plan.planning_session_id or planning_session_id

    if traveller_id and not trip_id and _looks_like_existing_context_follow_up(message):
        latest_trip = _get_latest_trip_for_traveller(db, traveller_id)
        if latest_trip is not None:
            trip_id = latest_trip.trip_id
            planning_session_id = planning_session_id or latest_trip.planning_session_id

    if traveller_id and not planning_session_id and _looks_like_existing_context_follow_up(message):
        latest_plan = _get_latest_plan_for_traveller(db, traveller_id)
        if latest_plan is not None:
            planning_session_id = latest_plan.planning_session_id

    if traveller_id and not trip_id and planning_session_id:
        trip_from_plan = _get_trip_by_planning_session(db, planning_session_id)
        if trip_from_plan is not None:
            trip_id = trip_from_plan.trip_id
            traveller_id = trip_from_plan.traveller_id
            planning_session_id = trip_from_plan.planning_session_id or planning_session_id

    return {
        "traveller_id": traveller_id,
        "planning_session_id": planning_session_id,
        "trip_id": trip_id,
    }


def classify_assistant_intent(payload: AssistantOrchestrateRequest) -> AssistantIntentClassification:
    message = payload.message.strip()
    lowered = message.lower()

    destinations = _extract_known_destinations(message)
    duration_days = _extract_duration_days(message)

    if payload.context.planning_session_id and any(
        token in lowered for token in ["replace", "swap", "change", "edit", "slot", "itinerary", "day "]
    ):
        return AssistantIntentClassification(
            intent="itinerary_follow_up",
            confidence=0.95,
            rationale="Detected itinerary-edit or itinerary-follow-up language with planning session context.",
            extracted_duration_days=duration_days,
        )

    if payload.context.trip_id and _looks_like_live_runtime_request(message):
        return AssistantIntentClassification(
            intent="live_runtime",
            confidence=0.94,
            rationale="Detected live-travel runtime language with an active saved trip context.",
            extracted_duration_days=duration_days,
        )

    if any(token in lowered for token in ["compare", "versus", " vs ", "better than", "which is better"]):
        return AssistantIntentClassification(
            intent="destination_compare",
            confidence=0.93 if len(destinations) >= 2 else 0.70,
            rationale="Detected explicit destination comparison language.",
            extracted_destination_a=destinations[0] if len(destinations) >= 1 else None,
            extracted_destination_b=destinations[1] if len(destinations) >= 2 else None,
            extracted_duration_days=duration_days,
        )

    if any(token in lowered for token in ["plan", "itinerary", "trip"]) and (
        duration_days is not None or len(destinations) >= 1
    ):
        return AssistantIntentClassification(
            intent="trip_plan_create",
            confidence=0.90,
            rationale="Detected trip-planning language with destination and/or duration signals.",
            extracted_destination_a=destinations[0] if len(destinations) >= 1 else None,
            extracted_duration_days=duration_days,
        )

    if any(token in lowered for token in ["guide", "what to do", "things to do", "where to stay", "neighborhood"]):
        return AssistantIntentClassification(
            intent="destination_guide",
            confidence=0.88,
            rationale="Detected destination-guide exploration language.",
            extracted_destination_a=destinations[0] if len(destinations) >= 1 else None,
            extracted_duration_days=duration_days,
        )

    if len(destinations) == 1 and duration_days is not None:
        return AssistantIntentClassification(
            intent="trip_plan_create",
            confidence=0.75,
            rationale="Defaulted to trip planning because the message includes one destination and a time horizon.",
            extracted_destination_a=destinations[0],
            extracted_duration_days=duration_days,
        )

    return AssistantIntentClassification(
        intent="unknown",
        confidence=0.40,
        rationale="Could not deterministically map the message to a supported assistant workflow.",
        extracted_destination_a=destinations[0] if len(destinations) >= 1 else None,
        extracted_destination_b=destinations[1] if len(destinations) >= 2 else None,
        extracted_duration_days=duration_days,
    )


def orchestrate_assistant_request(
    db: Session,
    payload: AssistantOrchestrateRequest,
) -> AssistantOrchestrateResponse:
    resolved_context = _resolve_assistant_context(db, payload)

    resolved_payload = AssistantOrchestrateRequest(
        message=payload.message,
        context=payload.context.__class__(**resolved_context),
        source_surface=payload.source_surface,
        stream=payload.stream,
    )
    classification = classify_assistant_intent(resolved_payload)

    if classification.intent == "live_runtime":
        if not resolved_context["traveller_id"] or not resolved_context["trip_id"]:
            return AssistantOrchestrateResponse(
                classification=classification,
                route="unknown",
                continuity_context=resolved_context,
                payload={"error": "traveller_id and trip_id are required for live runtime routing."},
            )

        result = orchestrate_live_runtime(
            db,
            LiveRuntimeOrchestrateRequest(
                traveller_id=resolved_context["traveller_id"],
                trip_id=resolved_context["trip_id"],
                planning_session_id=resolved_context["planning_session_id"],
                message=payload.message,
                source_surface=payload.source_surface,
            ),
        )
        return AssistantOrchestrateResponse(
            classification=classification,
            route="live_runtime.orchestrate",
            continuity_context={
                **resolved_context,
                "run_id": result.run.run_id,
            },
            payload=result.model_dump(mode="json"),
        )

    if classification.intent == "destination_guide":
        destination = classification.extracted_destination_a
        if not destination:
            return AssistantOrchestrateResponse(
                classification=classification,
                route="unknown",
                continuity_context=resolved_context,
                payload={"error": "No destination could be extracted for destination guide generation."},
            )

        result = build_destination_guide(
            DestinationGuideRequest(
                destination=destination,
                traveller_id=resolved_context["traveller_id"],
                duration_days=classification.extracted_duration_days or 3,
                traveller_type="solo",
                interests=[],
                pace_preference="balanced",
                budget="midrange",
            )
        )
        return AssistantOrchestrateResponse(
            classification=classification,
            route="destinations.guide",
            continuity_context=resolved_context,
            payload=result.model_dump(mode="json"),
        )

    if classification.intent == "destination_compare":
        if not classification.extracted_destination_a or not classification.extracted_destination_b:
            return AssistantOrchestrateResponse(
                classification=classification,
                route="unknown",
                continuity_context=resolved_context,
                payload={"error": "Two destinations are required for comparison routing."},
            )

        result = compare_destinations(
            DestinationComparisonRequest(
                destination_a=classification.extracted_destination_a,
                destination_b=classification.extracted_destination_b,
                traveller_id=resolved_context["traveller_id"],
                traveller_type="solo",
                interests=[],
                pace_preference="balanced",
                budget="midrange",
                duration_days=classification.extracted_duration_days or 3,
            )
        )
        return AssistantOrchestrateResponse(
            classification=classification,
            route="destinations.compare",
            continuity_context=resolved_context,
            payload=result.model_dump(mode="json"),
        )

    if classification.intent == "trip_plan_create":
        if not resolved_context["traveller_id"]:
            return AssistantOrchestrateResponse(
                classification=classification,
                route="unknown",
                continuity_context=resolved_context,
                payload={"error": "traveller_id is required for trip planning orchestration."},
            )

        result = parse_and_save_trip_brief(
            db,
            TripBriefParseRequest(
                traveller_id=resolved_context["traveller_id"],
                brief=payload.message,
                source_surface=payload.source_surface,
            ),
        )
        return AssistantOrchestrateResponse(
            classification=classification,
            route="trip_plans.parse_and_save",
            continuity_context={
                **resolved_context,
                "planning_session_id": result.planning_session_id,
            },
            payload=result.model_dump(mode="json"),
        )

    if classification.intent == "itinerary_follow_up":
        if not resolved_context["planning_session_id"]:
            return AssistantOrchestrateResponse(
                classification=classification,
                route="unknown",
                continuity_context=resolved_context,
                payload={"error": "planning_session_id is required for itinerary follow-up routing."},
            )

        result = get_trip_plan_summary(db, resolved_context["planning_session_id"])
        return AssistantOrchestrateResponse(
            classification=classification,
            route="trip_plans.get_summary",
            continuity_context=resolved_context,
            payload=result.model_dump(mode="json"),
        )

    return AssistantOrchestrateResponse(
        classification=classification,
        route="unknown",
        continuity_context=resolved_context,
        payload={
            "message": "The assistant router could not deterministically classify this message into a supported flow."
        },
    )


def stream_assistant_request(
    db: Session,
    payload: AssistantOrchestrateRequest,
) -> Generator[str, None, None]:
    resolved_context = _resolve_assistant_context(db, payload)

    resolved_payload = AssistantOrchestrateRequest(
        message=payload.message,
        context=payload.context.__class__(**resolved_context),
        source_surface=payload.source_surface,
        stream=payload.stream,
    )
    classification = classify_assistant_intent(resolved_payload)

    yield json.dumps(
        {
            "type": "meta",
            "intent": classification.intent,
            "confidence": classification.confidence,
            "rationale": classification.rationale,
            "continuity_context": resolved_context,
        }
    ) + "\n"

    if classification.intent == "live_runtime":
        if not resolved_context["traveller_id"] or not resolved_context["trip_id"]:
            yield json.dumps(
                {
                    "type": "final",
                    "payload": AssistantOrchestrateResponse(
                        classification=classification,
                        route="unknown",
                        continuity_context=resolved_context,
                        payload={"error": "traveller_id and trip_id are required for live runtime routing."},
                    ).model_dump(mode="json"),
                }
            ) + "\n"
            return

        live_payload = LiveRuntimeOrchestrateRequest(
            traveller_id=resolved_context["traveller_id"],
            trip_id=resolved_context["trip_id"],
            planning_session_id=resolved_context["planning_session_id"],
            message=payload.message,
            source_surface=payload.source_surface,
        )
        yield from stream_live_runtime(db, live_payload)
        return

    if classification.intent == "destination_guide" and classification.extracted_destination_a:
        guide_payload = DestinationGuideRequest(
            destination=classification.extracted_destination_a,
            traveller_id=resolved_context["traveller_id"],
            duration_days=classification.extracted_duration_days or 3,
            traveller_type="solo",
            interests=[],
            pace_preference="balanced",
            budget="midrange",
        )
        yield from stream_destination_guide(guide_payload)
        return

    result = orchestrate_assistant_request(db, payload)
    yield json.dumps(
        {
            "type": "final",
            "payload": result.model_dump(mode="json"),
        }
    ) + "\n"