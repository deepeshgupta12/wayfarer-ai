from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


TripBudget = Literal["budget", "midrange", "luxury"]
TripPace = Literal["relaxed", "balanced", "fast"]
TripGroup = Literal["solo", "couple", "family", "friends"]
TripInterest = Literal["food", "culture", "adventure", "nature", "luxury", "nightlife", "wellness"]
TripSlotType = Literal["morning", "lunch", "afternoon", "evening"]
TripSignalType = Literal["selected_place", "skipped_recommendation", "replaced_slot"]


class TripBriefParseRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    brief: str = Field(..., min_length=1)
    source_surface: str = Field(default="assistant")


class TripPlanUpdateRequest(BaseModel):
    destination: str | None = None
    duration_days: int | None = Field(default=None, ge=1, le=30)
    group_type: TripGroup | None = None
    interests: list[TripInterest] | None = None
    pace_preference: TripPace | None = None
    budget: TripBudget | None = None


class TripSlotReplacementRequest(BaseModel):
    day_number: int = Field(..., ge=1, le=30)
    slot_type: TripSlotType
    replacement_mode: Literal["best_alternative", "less_hectic", "more_food", "more_culture"] = Field(
        default="best_alternative"
    )
    preferred_location_id: str | None = None


class ParsedTripConstraints(BaseModel):
    destination: str | None = None
    duration_days: int | None = None
    group_type: TripGroup | None = None
    interests: list[TripInterest] = Field(default_factory=list)
    pace_preference: TripPace | None = None
    budget: TripBudget | None = None


class ComparisonPlanningOption(BaseModel):
    branch: Literal["destination_a", "destination_b"]
    location_id: str | None = None
    destination: str
    weighted_score: float
    why_pick_this: str


class ComparisonContext(BaseModel):
    comparison_id: str
    source_surface: str = "compare"
    destination_a: str
    destination_b: str
    selected_branch: Literal["destination_a", "destination_b"] | None = None
    selected_destination: str | None = None
    selected_location_id: str | None = None
    verdict: str | None = None
    planning_recommendation: str | None = None
    options: list[ComparisonPlanningOption] = Field(default_factory=list)


class TripPlanFromComparisonRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    source_surface: str = Field(default="compare")
    duration_days: int = Field(..., ge=1, le=30)
    group_type: TripGroup
    interests: list[TripInterest] = Field(default_factory=list)
    pace_preference: TripPace
    budget: TripBudget
    comparison_context: ComparisonContext


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
    geo_cluster: str | None = None
    related_locations: list["TripAlternativeSuggestion"] = Field(default_factory=list)


class TripAlternativeSuggestion(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    score: float
    why_alternative: str
    geo_cluster: str | None = None
    source_location_id: str | None = None
    relation_type: str | None = None
    city_match: bool = False


class TripSlotAssignment(BaseModel):
    slot_type: TripSlotType
    label: str
    summary: str
    assigned_place_name: str | None = None
    assigned_location_id: str | None = None
    rationale: str
    continuity_note: str | None = None
    movement_note: str | None = None
    alternatives: list[TripAlternativeSuggestion] = Field(default_factory=list)
    fallback_candidate_ids: list[str] = Field(default_factory=list)
    fallback_candidate_names: list[str] = Field(default_factory=list)


class TripDayPlan(BaseModel):
    day_number: int
    title: str
    summary: str
    place_names: list[str] = Field(default_factory=list)
    candidate_location_ids: list[str] = Field(default_factory=list)
    slots: list[TripSlotAssignment] = Field(default_factory=list)
    day_rationale: str
    continuity_strategy: str | None = None
    fallback_candidate_ids: list[str] = Field(default_factory=list)
    fallback_candidate_names: list[str] = Field(default_factory=list)
    geo_cluster: str | None = None


class TripPlanResponse(BaseModel):
    planning_session_id: str
    traveller_id: str
    source_surface: str
    raw_brief: str
    parsed_constraints: ParsedTripConstraints
    missing_fields: list[str] = Field(default_factory=list)
    status: str
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary_skeleton: list[TripDayPlan] = Field(default_factory=list)
    workspace_alternatives: list[TripAlternativeSuggestion] = Field(default_factory=list)
    comparison_context: ComparisonContext | None = None
    saved: bool
    comparison_context: ComparisonContext | None = None
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
    itinerary_skeleton: list[TripDayPlan] = Field(default_factory=list)
    workspace_alternatives: list[TripAlternativeSuggestion] = Field(default_factory=list)
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
    itinerary_skeleton: list[TripDayPlan] = Field(default_factory=list)
    workspace_alternatives: list[TripAlternativeSuggestion] = Field(default_factory=list)
    comparison_context: ComparisonContext | None = None
    saved: bool
    updated_at: datetime


class TripPromoteRequest(BaseModel):
    title: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    companions: TripGroup | None = None
    status: str = Field(default="planning")
    source_surface: str = Field(default="planner_modal")


class SavedTripSummaryResponse(BaseModel):
    trip_id: str
    traveller_id: str
    planning_session_id: str | None = None
    title: str
    destination: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    companions: str | None = None
    status: str
    source_surface: str
    current_version_number: int
    selected_places_count: int
    skipped_recommendations_count: int
    replaced_slots_count: int
    parsed_constraints: ParsedTripConstraints
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary: list[dict[str, object]] = Field(default_factory=list)
    itinerary_skeleton: list[TripDayPlan] = Field(default_factory=list)
    comparison_context: ComparisonContext | None = None
    created_at: datetime
    updated_at: datetime


class SavedTripListResponse(BaseModel):
    traveller_id: str
    total: int
    items: list[SavedTripSummaryResponse]


class TripVersionSnapshotRequest(BaseModel):
    snapshot_reason: str = Field(default="manual_snapshot", min_length=1)
    parsed_constraints: ParsedTripConstraints | None = None
    candidate_places: list[TripCandidatePlace] | None = None
    itinerary: list[dict[str, object]] | None = None
    itinerary_skeleton: list[TripDayPlan] | None = None
    comparison_context: ComparisonContext | None = None
    status: str | None = None


class TripVersionResponse(BaseModel):
    version_id: str
    trip_id: str
    traveller_id: str
    planning_session_id: str | None = None
    version_number: int
    snapshot_reason: str
    source_surface: str
    status: str
    parsed_constraints: ParsedTripConstraints
    candidate_places: list[TripCandidatePlace] = Field(default_factory=list)
    itinerary: list[dict[str, object]] = Field(default_factory=list)
    itinerary_skeleton: list[TripDayPlan] = Field(default_factory=list)
    comparison_context: ComparisonContext | None = None
    created_at: datetime


class TripVersionListResponse(BaseModel):
    trip_id: str
    total: int
    items: list[TripVersionResponse]


class TripSignalCreateRequest(BaseModel):
    signal_type: TripSignalType
    location_id: str | None = None
    day_number: int | None = Field(default=None, ge=1, le=30)
    slot_type: TripSlotType | None = None
    payload: dict[str, object] = Field(default_factory=dict)


class TripSignalResponse(BaseModel):
    signal_id: str
    trip_id: str
    traveller_id: str
    planning_session_id: str | None = None
    signal_type: str
    location_id: str | None = None
    day_number: int | None = None
    slot_type: str | None = None
    payload: dict[str, object] = Field(default_factory=dict)
    created_at: datetime


class TripSignalListResponse(BaseModel):
    trip_id: str
    total: int
    items: list[TripSignalResponse]

TripCandidatePlace.model_rebuild()
TripAlternativeSuggestion.model_rebuild()
TripPlanResponse.model_rebuild()
TripPlanSummaryResponse.model_rebuild()
TripPlanEnrichResponse.model_rebuild()
SavedTripSummaryResponse.model_rebuild()
TripVersionResponse.model_rebuild()