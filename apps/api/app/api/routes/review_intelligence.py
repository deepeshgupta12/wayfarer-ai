from fastapi import APIRouter

from app.db.session import get_db_session
from app.schemas.review_intelligence import (
    ReviewIntelligenceOutput,
    ReviewIntelligencePersistedOutput,
    ReviewIntelligenceRequest,
)
from app.services.review_intelligence_service import analyze_and_persist_reviews, analyze_reviews

router = APIRouter(prefix="/review-intelligence", tags=["review-intelligence"])


@router.post("/analyze", response_model=ReviewIntelligenceOutput)
def analyze_review_intelligence(
    payload: ReviewIntelligenceRequest,
) -> ReviewIntelligenceOutput:
    return analyze_reviews(payload)


@router.post("/analyze-and-save", response_model=ReviewIntelligencePersistedOutput)
def analyze_and_save_review_intelligence(
    payload: ReviewIntelligenceRequest,
) -> ReviewIntelligencePersistedOutput:
    db = get_db_session()
    try:
        return analyze_and_persist_reviews(db, payload)
    finally:
        db.close()