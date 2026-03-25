import math
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.models.persona import TravellerPersonaRecord
from app.schemas.persona import (
    TravellerPersonaInitializeRequest,
    TravellerPersonaInput,
    TravellerPersonaOutput,
    TravellerPersonaPersistedOutput,
)
from app.services.traveller_memory_service import get_recent_traveller_memory_records

ALLOWED_INTERESTS = ["food", "culture", "adventure", "nature", "luxury", "nightlife", "wellness"]
ALLOWED_PACES = ["relaxed", "balanced", "fast"]
ALLOWED_GROUPS = ["solo", "couple", "family", "friends"]
ALLOWED_STYLES = ["budget", "midrange", "luxury"]

QUERY_INTEREST_HINTS: dict[str, list[str]] = {
    "food": ["food", "foodie", "cuisine", "restaurant", "eat", "dining"],
    "culture": ["culture", "history", "heritage", "museum", "temple", "old town"],
    "adventure": ["adventure", "hiking", "trek", "outdoors", "kayak", "surf"],
    "nature": ["nature", "scenic", "park", "mountain", "beach", "river"],
    "luxury": ["luxury", "premium", "boutique", "fine dining", "upscale"],
    "nightlife": ["nightlife", "bar", "late night", "club", "music"],
    "wellness": ["wellness", "spa", "retreat", "relax", "onsen"],
}


def _detect_archetype(payload: TravellerPersonaInput) -> str:
    interests = set(payload.interests)

    if payload.travel_style == "luxury" or "luxury" in interests:
        return "luxury seeker"

    if payload.group_type == "family":
        return "family explorer"

    if "food" in interests and "culture" in interests:
        return "food and culture explorer"

    if "adventure" in interests and payload.pace_preference == "fast":
        return "adventure traveller"

    if payload.travel_style == "budget" and payload.group_type == "solo":
        return "budget backpacker"

    if "wellness" in interests and payload.pace_preference == "relaxed":
        return "slow wellness traveller"

    return "comfort-seeking explorer"


def _build_summary(archetype: str, payload: TravellerPersonaInput) -> str:
    interests_text = ", ".join(payload.interests)
    return (
        f"You travel like a {archetype} with a {payload.pace_preference} pace, "
        f"usually in a {payload.group_type} setting, with strong interest in {interests_text}."
    )


def _infer_interests_from_query(query: str) -> list[str]:
    lowered = query.lower()
    inferred: list[str] = []

    for interest, keywords in QUERY_INTEREST_HINTS.items():
        if any(keyword in lowered for keyword in keywords):
            inferred.append(interest)

    return inferred


def _normalize_distribution(scores: dict[str, float]) -> dict[str, float]:
    total = sum(scores.values())
    if total <= 0:
        uniform = 1.0 / len(scores)
        return {key: uniform for key in scores}

    return {key: value / total for key, value in scores.items()}


def _build_prior_distribution(
    allowed_values: Iterable[str],
    current_value: str,
    selected_weight: float = 0.64,
) -> dict[str, float]:
    allowed = list(allowed_values)
    if current_value not in allowed:
        current_value = allowed[0]

    remaining = max(1e-6, 1.0 - selected_weight)
    other_weight = remaining / max(1, len(allowed) - 1)

    priors: dict[str, float] = {}
    for value in allowed:
        priors[value] = selected_weight if value == current_value else other_weight
    return priors


def _build_interest_beta_priors(
    current_interests: list[str],
) -> dict[str, tuple[float, float]]:
    priors: dict[str, tuple[float, float]] = {}

    for interest in ALLOWED_INTERESTS:
        if interest in current_interests:
            priors[interest] = (2.5, 1.2)
        else:
            priors[interest] = (1.2, 2.0)

    return priors


def _posterior_from_likelihoods(
    prior: dict[str, float],
    likelihoods: list[dict[str, float]],
) -> dict[str, float]:
    log_scores = {key: math.log(max(value, 1e-9)) for key, value in prior.items()}

    for likelihood in likelihoods:
        for key, value in likelihood.items():
            log_scores[key] += math.log(max(value, 1e-9))

    max_log = max(log_scores.values())
    stabilized = {key: math.exp(value - max_log) for key, value in log_scores.items()}
    return _normalize_distribution(stabilized)


def _build_group_likelihood(payload: dict[str, object]) -> dict[str, float] | None:
    traveller_type = payload.get("traveller_type")
    if traveller_type not in ALLOWED_GROUPS:
        return None

    likelihood = {group: 0.85 / (len(ALLOWED_GROUPS) - 1) for group in ALLOWED_GROUPS}
    likelihood[traveller_type] = 0.85
    return _normalize_distribution(likelihood)


def _build_style_likelihood(payload: dict[str, object]) -> dict[str, float] | None:
    budget = payload.get("budget")
    if budget not in ALLOWED_STYLES:
        return None

    likelihood = {style: 0.8 / (len(ALLOWED_STYLES) - 1) for style in ALLOWED_STYLES}
    likelihood[budget] = 0.8
    return _normalize_distribution(likelihood)


def _build_pace_likelihood(payload: dict[str, object]) -> dict[str, float] | None:
    duration_days = payload.get("duration_days")
    if not isinstance(duration_days, int):
        return None

    if duration_days <= 2:
        target = "fast"
    elif duration_days >= 6:
        target = "relaxed"
    else:
        target = "balanced"

    likelihood = {pace: 0.8 / (len(ALLOWED_PACES) - 1) for pace in ALLOWED_PACES}
    likelihood[target] = 0.8
    return _normalize_distribution(likelihood)


def _update_interest_posteriors(
    priors: dict[str, tuple[float, float]],
    memory_payloads: list[dict[str, object]],
) -> dict[str, float]:
    posteriors: dict[str, tuple[float, float]] = {key: (a, b) for key, (a, b) in priors.items()}

    for payload in memory_payloads:
        declared_interests = payload.get("interests", [])
        declared_set = {
            interest
            for interest in declared_interests
            if isinstance(declared_interests, list) and interest in ALLOWED_INTERESTS
        }

        query = payload.get("query")
        inferred_set = set(_infer_interests_from_query(query)) if isinstance(query, str) else set()

        positive_evidence = declared_set | inferred_set
        if not positive_evidence:
            continue

        event_type = str(payload.get("_event_type", ""))
        weight = 1.35 if event_type == "destination_guide_generated" else 1.0

        for interest in ALLOWED_INTERESTS:
            alpha, beta = posteriors[interest]
            if interest in positive_evidence:
                alpha += 1.4 * weight
            else:
                beta += 0.15 * weight
            posteriors[interest] = (alpha, beta)

    return {
        interest: round(alpha / (alpha + beta), 4)
        for interest, (alpha, beta) in posteriors.items()
    }


def build_initial_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    archetype = _detect_archetype(payload)

    return TravellerPersonaOutput(
        archetype=archetype,
        summary=_build_summary(archetype, payload),
        signals={
            "travel_style": payload.travel_style,
            "pace_preference": payload.pace_preference,
            "group_type": payload.group_type,
            "interests": payload.interests,
        },
    )


def initialize_and_persist_persona(
    db: Session,
    payload: TravellerPersonaInitializeRequest,
) -> TravellerPersonaPersistedOutput:
    persona = build_initial_persona(payload)

    record = TravellerPersonaRecord(
        traveller_id=payload.traveller_id,
        archetype=persona.archetype,
        summary=persona.summary,
        travel_style=payload.travel_style,
        pace_preference=payload.pace_preference,
        group_type=payload.group_type,
        interests=list(payload.interests),
    )

    db.merge(record)
    db.commit()

    return TravellerPersonaPersistedOutput(
        traveller_id=payload.traveller_id,
        archetype=persona.archetype,
        summary=persona.summary,
        signals=persona.signals,
    )


def refresh_persona_from_memory(
    db: Session,
    traveller_id: str,
) -> TravellerPersonaPersistedOutput:
    record = db.get(TravellerPersonaRecord, traveller_id)
    if record is None:
        raise ValueError(f"Traveller persona not found for traveller_id={traveller_id}")

    memory_records = get_recent_traveller_memory_records(
        db=db,
        traveller_id=traveller_id,
        limit=25,
    )

    memory_payloads: list[dict[str, object]] = []
    for memory_record in memory_records:
        payload = memory_record.payload if isinstance(memory_record.payload, dict) else {}
        payload = dict(payload)
        payload["_event_type"] = memory_record.event_type
        memory_payloads.append(payload)

    group_prior = _build_prior_distribution(ALLOWED_GROUPS, record.group_type)
    pace_prior = _build_prior_distribution(ALLOWED_PACES, record.pace_preference)
    style_prior = _build_prior_distribution(ALLOWED_STYLES, record.travel_style)
    interest_priors = _build_interest_beta_priors(list(record.interests))

    group_likelihoods = [
        likelihood
        for payload in memory_payloads
        if (likelihood := _build_group_likelihood(payload)) is not None
    ]
    pace_likelihoods = [
        likelihood
        for payload in memory_payloads
        if (likelihood := _build_pace_likelihood(payload)) is not None
    ]
    style_likelihoods = [
        likelihood
        for payload in memory_payloads
        if (likelihood := _build_style_likelihood(payload)) is not None
    ]

    group_posterior = _posterior_from_likelihoods(group_prior, group_likelihoods)
    pace_posterior = _posterior_from_likelihoods(pace_prior, pace_likelihoods)
    style_posterior = _posterior_from_likelihoods(style_prior, style_likelihoods)
    interest_posteriors = _update_interest_posteriors(interest_priors, memory_payloads)

    updated_group = max(group_posterior.items(), key=lambda item: item[1])[0]
    updated_pace = max(pace_posterior.items(), key=lambda item: item[1])[0]
    updated_style = max(style_posterior.items(), key=lambda item: item[1])[0]

    ranked_interests = [
        interest
        for interest, probability in sorted(
            interest_posteriors.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )
        if probability >= 0.45
    ]
    updated_interests = ranked_interests[:3] or list(record.interests)

    refined_payload = TravellerPersonaInput(
        travel_style=updated_style,
        pace_preference=updated_pace,
        group_type=updated_group,
        interests=updated_interests,
    )

    refined_persona = build_initial_persona(refined_payload)

    record.archetype = refined_persona.archetype
    record.summary = refined_persona.summary
    record.travel_style = updated_style
    record.pace_preference = updated_pace
    record.group_type = updated_group
    record.interests = list(updated_interests)

    db.add(record)
    db.commit()

    return TravellerPersonaPersistedOutput(
        traveller_id=traveller_id,
        archetype=refined_persona.archetype,
        summary=refined_persona.summary,
        signals={
            "travel_style": updated_style,
            "pace_preference": updated_pace,
            "group_type": updated_group,
            "interests": updated_interests,
            "memory_events_used": len(memory_payloads),
            "updated_from_memory": True,
            "bayesian_update_v1": True,
            "posterior": {
                "group_type": group_posterior,
                "pace_preference": pace_posterior,
                "travel_style": style_posterior,
                "interests": interest_posteriors,
            },
        },
    )