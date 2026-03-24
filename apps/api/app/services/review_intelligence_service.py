from sqlalchemy.orm import Session

from app.models.review_intelligence import ReviewIntelligenceRecord
from app.schemas.review_intelligence import (
    ReviewIntelligenceOutput,
    ReviewIntelligencePersistedOutput,
    ReviewIntelligenceRequest,
)


def _classify_theme(combined_text: str, keywords: list[str]) -> str:
    lowered = combined_text.lower()
    hits = sum(1 for keyword in keywords if keyword in lowered)

    if hits >= 2:
        return "positive"
    if hits == 1:
        return "neutral"
    return "caution"


def _compute_trust_score(reviews: list[dict[str, object]]) -> float:
    review_count = len(reviews)
    short_review_count = sum(1 for review in reviews if len(str(review["text"]).strip()) < 20)

    base_score = min(0.95, 0.55 + (review_count * 0.07))
    penalty = 0.08 if short_review_count > review_count / 2 else 0.0

    return round(max(0.2, base_score - penalty), 2)


def _label_authenticity(trust_score: float) -> str:
    if trust_score >= 0.8:
        return "high"
    if trust_score >= 0.6:
        return "medium"
    return "low"


def analyze_reviews(payload: ReviewIntelligenceRequest) -> ReviewIntelligenceOutput:
    combined_text = " ".join(review.text for review in payload.reviews)
    average_rating = sum(review.rating for review in payload.reviews) / len(payload.reviews)

    themes = {
        "service": _classify_theme(combined_text, ["friendly", "helpful", "staff", "service"]),
        "food_quality": _classify_theme(combined_text, ["tasty", "delicious", "fresh", "flavor"]),
        "value": _classify_theme(combined_text, ["value", "worth", "price", "expensive"]),
        "ambience": _classify_theme(combined_text, ["beautiful", "cozy", "ambience", "atmosphere"]),
    }

    if average_rating >= 4.3:
        verdict_prefix = "Travellers consistently rate this place highly."
    elif average_rating >= 3.5:
        verdict_prefix = "Travellers generally like this place with a few mixed signals."
    else:
        verdict_prefix = "Travellers report a mixed-to-cautious experience here."

    trust_score = _compute_trust_score(
        [{"rating": review.rating, "text": review.text} for review in payload.reviews]
    )
    authenticity_label = _label_authenticity(trust_score)

    quick_verdict = (
        f"{verdict_prefix} Review signals suggest strongest confidence around "
        f"service={themes['service']}, food_quality={themes['food_quality']}, "
        f"value={themes['value']}, ambience={themes['ambience']}."
    )

    return ReviewIntelligenceOutput(
        location_id=payload.location_id,
        location_name=payload.location_name,
        quick_verdict=quick_verdict,
        themes=themes,
        trust_score=trust_score,
        authenticity_label=authenticity_label,
        review_count=len(payload.reviews),
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