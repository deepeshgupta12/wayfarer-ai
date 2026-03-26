from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db_session
from app.models.review_intelligence import ReviewIntelligenceRecord
from app.providers.ollama_provider import OllamaChatProvider
from app.providers.openai_provider import OpenAIChatProvider
from app.schemas.review_intelligence import (
    ReviewIntelligenceOutput,
    ReviewIntelligencePersistedOutput,
    ReviewIntelligenceRequest,
)

THEME_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "service": {
        "positive": ["friendly", "helpful", "staff", "service", "welcoming", "kind", "attentive"],
        "negative": ["rude", "slow service", "unhelpful", "ignored", "hostile", "poor service"],
    },
    "food_quality": {
        "positive": ["tasty", "delicious", "fresh", "flavor", "excellent food", "great food"],
        "negative": ["bland", "cold food", "overcooked", "bad food", "stale", "flavourless"],
    },
    "value": {
        "positive": ["value", "worth", "fair price", "reasonable", "good price"],
        "negative": ["expensive", "overpriced", "not worth", "too pricey", "poor value"],
    },
    "ambience": {
        "positive": ["beautiful", "cozy", "ambience", "atmosphere", "charming", "lovely"],
        "negative": ["noisy", "crowded", "dirty", "chaotic", "uncomfortable", "soulless"],
    },
}

ALLOWED_THEME_LABELS = {"positive", "neutral", "caution"}


def _resolve_chat_provider():
    settings = get_settings()
    if settings.default_llm_provider == "ollama":
        return OllamaChatProvider()
    return OpenAIChatProvider()


def _build_review_theme_prompt(
    location_name: str,
    reviews: list[dict[str, object]],
) -> str:
    review_lines = []
    for index, review in enumerate(reviews[:8], start=1):
        review_lines.append(
            f"{index}. rating={review['rating']} text={str(review['text']).strip()}"
        )

    return (
        "You are extracting structured travel review themes.\n"
        f"Location: {location_name}\n"
        "Classify each theme with one label: positive, neutral, or caution.\n"
        "Themes: service, food_quality, value, ambience.\n"
        "Return JSON only.\n"
        "Reviews:\n"
        + "\n".join(review_lines)
    )


def _build_review_theme_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "service": {"type": "string", "enum": ["positive", "neutral", "caution"]},
            "food_quality": {"type": "string", "enum": ["positive", "neutral", "caution"]},
            "value": {"type": "string", "enum": ["positive", "neutral", "caution"]},
            "ambience": {"type": "string", "enum": ["positive", "neutral", "caution"]},
        },
        "required": ["service", "food_quality", "value", "ambience"],
        "additionalProperties": False,
    }


def _sanitize_llm_theme_output(payload: dict[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(payload, dict):
        return None

    cleaned: dict[str, str] = {}
    for theme_name in THEME_KEYWORDS:
        value = payload.get(theme_name)
        if not isinstance(value, str):
            return None

        normalized = value.strip().lower()
        if normalized not in ALLOWED_THEME_LABELS:
            return None

        cleaned[theme_name] = normalized

    return cleaned


def _extract_themes_with_llm(
    location_name: str,
    reviews: list[dict[str, object]],
) -> dict[str, str] | None:
    provider = _resolve_chat_provider()
    prompt = _build_review_theme_prompt(location_name=location_name, reviews=reviews)
    schema = _build_review_theme_schema()

    try:
        raw_output = provider.generate_json(prompt=prompt, schema=schema)
    except Exception:
        return None

    return _sanitize_llm_theme_output(raw_output)


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _classify_theme(
    combined_text: str,
    positive_keywords: list[str],
    negative_keywords: list[str],
) -> str:
    positive_hits = _count_keyword_hits(combined_text, positive_keywords)
    negative_hits = _count_keyword_hits(combined_text, negative_keywords)

    if positive_hits >= 2 and negative_hits == 0:
        return "positive"
    if positive_hits > negative_hits:
        return "positive"
    if positive_hits == 0 and negative_hits == 0:
        return "neutral"
    if positive_hits == negative_hits:
        return "neutral"
    return "caution"


def _extract_themes_heuristically(
    combined_text: str,
) -> dict[str, str]:
    return {
        theme_name: _classify_theme(
            combined_text=combined_text,
            positive_keywords=theme_keywords["positive"],
            negative_keywords=theme_keywords["negative"],
        )
        for theme_name, theme_keywords in THEME_KEYWORDS.items()
    }


def _compute_trust_score(reviews: list[dict[str, object]]) -> float:
    review_count = len(reviews)
    short_review_count = sum(1 for review in reviews if len(str(review["text"]).strip()) < 20)

    ratings = [float(review["rating"]) for review in reviews]
    average_rating = sum(ratings) / review_count
    spread_penalty = 0.05 if max(ratings) - min(ratings) >= 3 else 0.0

    base_score = min(0.95, 0.55 + (review_count * 0.07))
    brevity_penalty = 0.08 if short_review_count > review_count / 2 else 0.0
    rating_penalty = 0.05 if average_rating < 3.5 else 0.0

    return round(max(0.2, base_score - brevity_penalty - spread_penalty - rating_penalty), 2)


def _label_authenticity(trust_score: float) -> str:
    if trust_score >= 0.8:
        return "high"
    if trust_score >= 0.6:
        return "medium"
    return "low"


def _normalize_reviews_for_signature(
    reviews: list[dict[str, object]],
) -> list[dict[str, object]]:
    normalized = [
        {
            "rating": int(review["rating"]),
            "text": str(review["text"]).strip(),
        }
        for review in reviews
    ]
    normalized.sort(key=lambda item: (item["rating"], item["text"]))
    return normalized


def _build_review_signature(reviews: list[dict[str, object]]) -> str:
    normalized_reviews = _normalize_reviews_for_signature(reviews)
    serialized = json.dumps(normalized_reviews, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _record_to_output(record: ReviewIntelligenceRecord) -> ReviewIntelligenceOutput:
    return ReviewIntelligenceOutput(
        location_id=record.location_id,
        location_name=record.location_name,
        quick_verdict=record.quick_verdict,
        themes=dict(record.themes or {}),
        trust_score=record.trust_score,
        authenticity_label=record.authenticity_label,
        review_count=record.review_count,
    )


def _record_to_persisted_output(
    record: ReviewIntelligenceRecord,
    cache_status: str,
) -> ReviewIntelligencePersistedOutput:
    return ReviewIntelligencePersistedOutput(
        location_id=record.location_id,
        location_name=record.location_name,
        quick_verdict=record.quick_verdict,
        themes=dict(record.themes or {}),
        trust_score=record.trust_score,
        authenticity_label=record.authenticity_label,
        review_count=record.review_count,
        saved=True,
        cache_status=cache_status,
    )


def _analyze_review_bundle_live(
    location_id: str,
    location_name: str,
    reviews: list[dict[str, object]],
) -> ReviewIntelligenceOutput:
    combined_text = " ".join(str(review["text"]) for review in reviews)
    average_rating = sum(float(review["rating"]) for review in reviews) / len(reviews)

    llm_themes = _extract_themes_with_llm(
        location_name=location_name,
        reviews=reviews,
    )
    themes = llm_themes or _extract_themes_heuristically(combined_text)

    if average_rating >= 4.3:
        verdict_prefix = "Travellers consistently rate this place highly."
    elif average_rating >= 3.5:
        verdict_prefix = "Travellers generally like this place, though some signals are mixed."
    else:
        verdict_prefix = "Travellers report a mixed-to-cautious experience here."

    trust_score = _compute_trust_score(reviews)
    authenticity_label = _label_authenticity(trust_score)

    quick_verdict = (
        f"{verdict_prefix} Review signals suggest strongest confidence around "
        f"service={themes['service']}, food_quality={themes['food_quality']}, "
        f"value={themes['value']}, ambience={themes['ambience']}."
    )

    return ReviewIntelligenceOutput(
        location_id=location_id,
        location_name=location_name,
        quick_verdict=quick_verdict,
        themes=themes,
        trust_score=trust_score,
        authenticity_label=authenticity_label,
        review_count=len(reviews),
    )


def get_persisted_review_intelligence(
    db: Session,
    location_id: str,
) -> ReviewIntelligencePersistedOutput | None:
    record = db.get(ReviewIntelligenceRecord, location_id)
    if record is None:
        return None
    return _record_to_persisted_output(record, cache_status="persisted")


def _upsert_review_intelligence_record(
    db: Session,
    analysis: ReviewIntelligenceOutput,
    review_signature: str,
    cache_status: str,
) -> ReviewIntelligencePersistedOutput:
    now = datetime.now(timezone.utc)

    record = db.get(ReviewIntelligenceRecord, analysis.location_id)
    if record is None:
        record = ReviewIntelligenceRecord(
            location_id=analysis.location_id,
            location_name=analysis.location_name,
            quick_verdict=analysis.quick_verdict,
            themes=analysis.themes,
            trust_score=analysis.trust_score,
            authenticity_label=analysis.authenticity_label,
            review_count=analysis.review_count,
            review_signature=review_signature,
            refreshed_at=now,
        )
        db.add(record)
    else:
        record.location_name = analysis.location_name
        record.quick_verdict = analysis.quick_verdict
        record.themes = analysis.themes
        record.trust_score = analysis.trust_score
        record.authenticity_label = analysis.authenticity_label
        record.review_count = analysis.review_count
        record.review_signature = review_signature
        record.refreshed_at = now

    db.commit()
    db.refresh(record)

    return _record_to_persisted_output(record, cache_status=cache_status)


def get_or_refresh_review_intelligence(
    db: Session,
    location_id: str,
    location_name: str,
    reviews: list[dict[str, object]],
    force_refresh: bool = False,
) -> ReviewIntelligencePersistedOutput:
    review_signature = _build_review_signature(reviews)
    existing = db.get(ReviewIntelligenceRecord, location_id)

    if (
        existing is not None
        and not force_refresh
        and existing.review_signature == review_signature
        and existing.review_count == len(reviews)
    ):
        if existing.location_name != location_name:
            existing.location_name = location_name
            db.add(existing)
            db.commit()
            db.refresh(existing)
        return _record_to_persisted_output(existing, cache_status="reused")

    live_analysis = _analyze_review_bundle_live(
        location_id=location_id,
        location_name=location_name,
        reviews=reviews,
    )

    cache_status = "refreshed" if existing is not None else "persisted"
    return _upsert_review_intelligence_record(
        db=db,
        analysis=live_analysis,
        review_signature=review_signature,
        cache_status=cache_status,
    )


def analyze_review_bundle(
    location_id: str,
    location_name: str,
    reviews: list[dict[str, object]],
) -> ReviewIntelligenceOutput:
    local_db: Session | None = None
    try:
        local_db = get_db_session()
        persisted = get_or_refresh_review_intelligence(
            db=local_db,
            location_id=location_id,
            location_name=location_name,
            reviews=reviews,
        )
        return ReviewIntelligenceOutput(
            location_id=persisted.location_id,
            location_name=persisted.location_name,
            quick_verdict=persisted.quick_verdict,
            themes=persisted.themes,
            trust_score=persisted.trust_score,
            authenticity_label=persisted.authenticity_label,
            review_count=persisted.review_count,
        )
    except Exception:
        return _analyze_review_bundle_live(
            location_id=location_id,
            location_name=location_name,
            reviews=reviews,
        )
    finally:
        if local_db is not None:
            local_db.close()


def analyze_reviews(payload: ReviewIntelligenceRequest) -> ReviewIntelligenceOutput:
    reviews = [{"rating": review.rating, "text": review.text} for review in payload.reviews]
    return _analyze_review_bundle_live(
        location_id=payload.location_id,
        location_name=payload.location_name,
        reviews=reviews,
    )


def analyze_and_persist_reviews(
    db: Session,
    payload: ReviewIntelligenceRequest,
) -> ReviewIntelligencePersistedOutput:
    reviews = [{"rating": review.rating, "text": review.text} for review in payload.reviews]
    return get_or_refresh_review_intelligence(
        db=db,
        location_id=payload.location_id,
        location_name=payload.location_name,
        reviews=reviews,
    )