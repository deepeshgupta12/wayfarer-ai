from typing import Literal

from pydantic import BaseModel, Field


TravellerType = Literal["solo", "couple", "family", "friends"]


class DestinationSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
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
    duration_days: int = Field(..., ge=1, le=30)
    traveller_type: TravellerType
    interests: list[str] = Field(default_factory=list)
    pace_preference: str = Field(default="balanced")
    budget: str = Field(default="midrange")


class DestinationGuideResponse(BaseModel):
    destination: str
    traveller_type: str
    duration_days: int
    overview: str
    highlights: list[str]
    suggested_areas: list[str]
    reasoning: list[str]
    review_summary: str | None = None
    review_signals: dict[str, str] = Field(default_factory=dict)
    review_authenticity: str | None = None