from typing import Literal

from pydantic import BaseModel, Field


TravellerType = Literal["solo", "couple", "family", "friends"]


class DestinationSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    traveller_id: str | None = Field(default=None, min_length=1)
    traveller_type: TravellerType | None = None
    interests: list[str] = Field(default_factory=list)


class DestinationSearchResult(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    rating: float
    review_count: int


class DestinationSearchResponse(BaseModel):
    query: str
    results: list[DestinationSearchResult]


class DestinationGuideRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    traveller_id: str | None = Field(default=None, min_length=1)
    duration_days: int = Field(..., ge=1, le=30)
    traveller_type: TravellerType
    interests: list[str] = Field(default_factory=list)
    pace_preference: str = Field(default="balanced")
    budget: str = Field(default="midrange")


class DestinationAreaCard(BaseModel):
    name: str
    category: str = "area"
    rating: float | None = None
    summary: str
    why_it_fits: str


class DestinationReviewInsight(BaseModel):
    overall_vibe: str
    standout_themes: list[str] = Field(default_factory=list)
    confidence: str
    raw_summary: str | None = None


class DestinationAlternative(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    match_score: float
    reason: str


class DestinationGuideResponse(BaseModel):
    destination: str
    traveller_type: str
    duration_days: int
    overview: str
    highlights: list[str]
    suggested_areas: list[str]
    area_cards: list[DestinationAreaCard] = Field(default_factory=list)
    reasoning: list[str]
    review_summary: str | None = None
    review_signals: dict[str, str] = Field(default_factory=dict)
    review_authenticity: str | None = None
    review_insight: DestinationReviewInsight | None = None
    youd_also_love: list[DestinationAlternative] = Field(default_factory=list)


class DestinationPlaceIndexRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    traveller_type: TravellerType | None = None
    interests: list[str] = Field(default_factory=list)


class DestinationPlaceIndexItem(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    embedding_dimensions: int


class DestinationPlaceIndexResponse(BaseModel):
    destination: str
    indexed_count: int
    items: list[DestinationPlaceIndexItem]


class SimilarPlaceMatch(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    similarity_score: float
    why_similar: str | None = None


class SimilarPlaceRequest(BaseModel):
    source_location_id: str = Field(..., min_length=1)
    top_k: int = Field(default=3, ge=1, le=10)
    city_filter: str | None = None


class SimilarPlaceResponse(BaseModel):
    source_location_id: str
    city_filter_applied: str | None = None
    matches: list[SimilarPlaceMatch]


class DestinationComparisonRequest(BaseModel):
    destination_a: str = Field(..., min_length=1)
    destination_b: str = Field(..., min_length=1)
    traveller_id: str | None = Field(default=None, min_length=1)
    traveller_type: TravellerType = Field(default="solo")
    interests: list[str] = Field(default_factory=list)
    pace_preference: str = Field(default="balanced")
    budget: str = Field(default="midrange")
    duration_days: int = Field(default=3, ge=1, le=30)


class DestinationComparisonSide(BaseModel):
    name: str
    city: str
    country: str
    category: str
    tagline: str
    best_for: str
    review_summary: str | None = None
    review_authenticity: str | None = None
    suggested_areas: list[str] = Field(default_factory=list)
    weighted_score: float


class DestinationComparisonDimension(BaseModel):
    name: str
    weight: float
    score_a: float
    score_b: float
    note_a: str
    note_b: str
    winner: Literal["destination_a", "destination_b", "tie"]


class DestinationComparisonResponse(BaseModel):
    destination_a: DestinationComparisonSide
    destination_b: DestinationComparisonSide
    dimensions: list[DestinationComparisonDimension] = Field(default_factory=list)
    verdict: str
    planning_recommendation: str
    next_step_suggestions: list[str] = Field(default_factory=list)