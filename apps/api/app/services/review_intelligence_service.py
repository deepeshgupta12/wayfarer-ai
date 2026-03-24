from sqlalchemy.orm import Session

from app.models.review_intelligence import ReviewIntelligenceRecord
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


def _count_keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for keyword in keywords if keyword in lowered)


def _classify_theme(combined_text: str, positive_keywords: list[str], negative_keywords: list[str]) -> str:
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


def analyze_review_bundle(
    location_id: str,
    location_name: str,
    reviews: list[dict[str, object]],
) -> ReviewIntelligenceOutput:
    combined_text = " ".join(str(review["text"]) for review in reviews)
    average_rating = sum(float(review["rating"]) for review in reviews) / len(reviews)

    themes = {
        theme_name: _classify_theme(
            combined_text=combined_text,
            positive_keywords=theme_keywords["positive"],
            negative_keywords=theme_keywords["negative"],
        )
        for theme_name, theme_keywords in THEME_KEYWORDS.items()
    }

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


def analyze_reviews(payload: ReviewIntelligenceRequest) -> ReviewIntelligenceOutput:
    reviews = [{"rating": review.rating, "text": review.text} for review in payload.reviews]
    return analyze_review_bundle(
        location_id=payload.location_id,
        location_name=payload.location_name,
        reviews=reviews,
    )


def analyze_and_persist_reviews(
    db: Session,
    payload: ReviewIntelligenceRequest,
) -> ReviewIntelligencePersistedOutput:
    result = analyze_reviews(payload)

    record = ReviewIntelligenceRecord(
        location_id=result.location_id,
        location_name=result.location_name,
        quick_verdict=result.quick_verdict,
        themes=result.themes,
        trust_score=result.trust_score,
        authenticity_label=result.authenticity_label,
        review_count=result.review_count,
    )

    db.merge(record)
    db.commit()

    return ReviewIntelligencePersistedOutput(
        location_id=result.location_id,
        location_name=result.location_name,
        quick_verdict=result.quick_verdict,
        themes=result.themes,
        trust_score=result.trust_score,
        authenticity_label=result.authenticity_label,
        review_count=result.review_count,
        saved=True,
    )