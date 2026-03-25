from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TripBudget = Literal["budget", "midrange", "luxury"]
TripPace = Literal["relaxed", "balanced", "fast"]
TripGroup = Literal["solo", "couple", "family", "friends"]
TripInterest = Literal["food", "culture", "adventure", "nature", "luxury", "nightlife", "wellness"]


class TripBriefParseRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    brief: str = Field(..., min_length=1)
    source_surface: str = Field(default="assistant")


class ParsedTripConstraints(BaseModel):
    destination: str | None = None
    duration_days: int | None = None
    group_type: TripGroup | None = None
    interests: list[TripInterest] = Field(default_factory=list)
    pace_preference: TripPace | None = None
    budget: TripBudget | None = None


class TripCandidatePlace(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    rating: float
    review_count: int
    review_authenticity: str | None = None
    review_summary: str | None = None
    score: float
    why_selected: str


class TripDaySkeleton(BaseModel):
    day_number: int
    title: str
    summary: str
    place_names: list[str] = Field(default_factory=list)
    candidate_location_ids: list[str] = Field(default_factory=list)


class TripPlanResponse(BaseModel):
    planning_session_id: str
    traveller_id: str
    source_surface: str
    raw_brief: str
    parsed_constraints: ParsedTripConstraints
    missing_fields: list[str] = Field(default_factory=list)
    status: str
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary_skeleton: list[TripDaySkeleton] = Field(default_factory=list)
    saved: bool
    created_at: datetime


class TripPlanSummaryResponse(BaseModel):
    planning_session_id: str
    traveller_id: str
    source_surface: str
    raw_brief: str
    parsed_constraints: ParsedTripConstraints
    missing_fields: list[str] = Field(default_factory=list)
    status: str
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary_skeleton: list[TripDaySkeleton] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class TripPlanEnrichResponse(BaseModel):
    planning_session_id: str
    traveller_id: str
    source_surface: str
    raw_brief: str
    parsed_constraints: ParsedTripConstraints
    missing_fields: list[str] = Field(default_factory=list)
    status: str
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary_skeleton: list[TripDaySkeleton] = Field(default_factory=list)
    saved: bool
    updated_at: datetime