from typing import Any, Literal

from pydantic import BaseModel, Field


TravellerType = Literal["solo", "couple", "family", "friends"]

class PlacePhotoAsset(BaseModel):
    photo_id: str
    location_id: str
    image_url: str
    source: str = "google_places"
    width: int | None = None
    height: int | None = None
    aspect_ratio: float | None = None
    caption: str | None = None
    tags: list[str] = Field(default_factory=list)
    scene_type: str | None = None
    visual_score: float = 0.0
    why_ranked: str | None = None

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
    photos: list[PlacePhotoAsset] = Field(default_factory=list)


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
    source_location_id: str | None = None
    relation_type: str | None = None
    source: str = "profile"
    city_match: bool = False
    photos: list[PlacePhotoAsset] = Field(default_factory=list)


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
    featured_photos: list[PlacePhotoAsset] = Field(default_factory=list)
    hidden_gems: list["HiddenGemRecommendation"] = Field(default_factory=list)


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
    photo_count: int = 0
    preview_photos: list[PlacePhotoAsset] = Field(default_factory=list)


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
    relation_type: str | None = None
    source: str = "embedding"
    city_match: bool = False


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
    location_id: str | None = None
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
    hero_photos: list[PlacePhotoAsset] = Field(default_factory=list)


class DestinationComparisonDimension(BaseModel):
    name: str
    weight: float
    score_a: float
    score_b: float
    note_a: str
    note_b: str
    winner: Literal["destination_a", "destination_b", "tie"]

class ComparisonPlanStartOption(BaseModel):
    branch: Literal["destination_a", "destination_b"]
    location_id: str | None = None
    destination: str
    weighted_score: float
    recommended: bool


class DestinationComparisonResponse(BaseModel):
    comparison_id: str
    destination_a: DestinationComparisonSide
    destination_b: DestinationComparisonSide
    dimensions: list[DestinationComparisonDimension] = Field(default_factory=list)
    verdict: str
    planning_recommendation: str
    next_step_suggestions: list[str] = Field(default_factory=list)
    youd_also_love: list[DestinationAlternative] = Field(default_factory=list)
    plan_start_options: list[ComparisonPlanStartOption] = Field(default_factory=list)

class HiddenGemRecommendation(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    rating: float
    review_count: int
    gem_score: float
    persona_relevance_score: float | None = None
    underrated_signal: bool = False
    why_hidden_gem: str
    fit_reasons: list[str] = Field(default_factory=list)
    source_context: str = "destination_pool"
    photos: list[PlacePhotoAsset] = Field(default_factory=list)


class HiddenGemDiscoveryRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    traveller_id: str | None = None
    traveller_type: str = Field(default="solo")
    interests: list[str] = Field(default_factory=list)
    pace_preference: str = Field(default="balanced")
    budget: str = Field(default="midrange")
    limit: int = Field(default=5, ge=1, le=10)


class HiddenGemDiscoveryResponse(BaseModel):
    destination: str
    total: int
    gems: list[HiddenGemRecommendation] = Field(default_factory=list)


NearbyTransportMode = Literal["walk", "transit", "drive"]

class NearbyDiscoveryContext(BaseModel):
    traveller_id: str | None = Field(default=None, min_length=1)
    trip_id: str | None = Field(default=None, min_length=1)
    planning_session_id: str | None = Field(default=None, min_length=1)
    intent_hint: str | None = None
    transport_mode: NearbyTransportMode = Field(default="walk")
    budget: str | None = None
    current_day_number: int | None = Field(default=None, ge=1, le=30)
    current_slot_type: str | None = None
    available_minutes: int | None = Field(default=None, ge=1, le=1440)
    current_place_name: str | None = None
    current_city: str | None = None
    current_country: str | None = None
    open_now_only: bool = False
    exclude_location_ids: list[str] = Field(default_factory=list)
    rejected_location_ids: list[str] = Field(default_factory=list)
    closed_location_ids: list[str] = Field(default_factory=list)
    unavailable_location_ids: list[str] = Field(default_factory=list)
    context_payload: dict[str, Any] = Field(default_factory=dict)


class NearbyDiscoveryRequest(BaseModel):
    latitude: float
    longitude: float
    city: str | None = None
    country: str | None = None
    query: str | None = None
    traveller_id: str | None = Field(default=None, min_length=1)
    traveller_type: TravellerType | None = None
    interests: list[str] = Field(default_factory=list)
    budget: str = Field(default="midrange")
    limit: int = Field(default=5, ge=1, le=10)
    starting_radius_meters: int = Field(default=800, ge=100, le=5000)
    max_radius_meters: int = Field(default=3000, ge=500, le=10000)
    adaptive_radius: bool = True
    source_surface: str = Field(default="nearby")
    context: NearbyDiscoveryContext | None = None


class NearbyPlaceRecommendation(BaseModel):
    location_id: str
    name: str
    city: str
    country: str
    category: str
    rating: float
    review_count: int
    distance_meters: int
    walking_minutes: int | None = None
    price_level: str | None = None
    open_now: bool | None = None
    source: str = "nearby"
    live_score: float
    fit_reasons: list[str] = Field(default_factory=list)
    why_recommended: str
    walking_friendly: bool = False
    photos: list[PlacePhotoAsset] = Field(default_factory=list)


class NearbyDiscoveryResponse(BaseModel):
    city: str | None = None
    country: str | None = None
    query: str | None = None
    total: int
    radius_used_meters: int
    search_expansions: list[int] = Field(default_factory=list)
    blocked_location_ids: list[str] = Field(default_factory=list)
    recommendations: list[NearbyPlaceRecommendation] = Field(default_factory=list)
    walking_alternatives: list[NearbyPlaceRecommendation] = Field(default_factory=list)
    fallbacks: list[NearbyPlaceRecommendation] = Field(default_factory=list)