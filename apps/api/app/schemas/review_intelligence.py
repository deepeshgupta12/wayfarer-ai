from typing import Literal

from pydantic import BaseModel, Field


ThemeLabel = Literal["positive", "neutral", "caution"]
AuthenticityLabel = Literal["high", "medium", "low"]


class ReviewItem(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    text: str = Field(..., min_length=1)


class ReviewIntelligenceRequest(BaseModel):
    location_id: str = Field(..., min_length=1)
    location_name: str = Field(..., min_length=1)
    reviews: list[ReviewItem] = Field(..., min_length=1)


class ReviewIntelligenceOutput(BaseModel):
    location_id: str
    location_name: str
    quick_verdict: str
    themes: dict[str, ThemeLabel]
    trust_score: float
    authenticity_label: AuthenticityLabel
    review_count: int


class ReviewIntelligencePersistedOutput(ReviewIntelligenceOutput):
    saved: bool