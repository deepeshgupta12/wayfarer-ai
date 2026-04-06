from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.review_intelligence import (
    ReviewIntelligenceOutput,
    ReviewIntelligencePersistedOutput,
    ReviewIntelligenceRequest,
)
from app.services.review_intelligence_service import (
    analyze_and_persist_reviews,
    analyze_reviews,
    get_persisted_review_intelligence,
)

router = APIRouter(prefix="/review-intelligence", tags=["review-intelligence"])


@router.post("/analyze", response_model=ReviewIntelligenceOutput)
def analyze_review_intelligence(
    payload: ReviewIntelligenceRequest,
) -> ReviewIntelligenceOutput:
    return analyze_reviews(payload)


@router.post("/analyze-and-save", response_model=ReviewIntelligencePersistedOutput)
def analyze_and_save_review_intelligence(
    payload: ReviewIntelligenceRequest,
    db: Session = Depends(get_db),
) -> ReviewIntelligencePersistedOutput:
    return analyze_and_persist_reviews(db, payload)


@router.get("/{location_id}", response_model=ReviewIntelligencePersistedOutput)
def get_saved_review_intelligence(
    location_id: str,
    db: Session = Depends(get_db),
) -> ReviewIntelligencePersistedOutput:
    result = get_persisted_review_intelligence(db, location_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Review intelligence not found")
    return result
