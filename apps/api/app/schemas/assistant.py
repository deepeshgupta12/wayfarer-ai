from typing import Any, Literal

from pydantic import BaseModel, Field


AssistantIntent = Literal[
    "destination_guide",
    "destination_compare",
    "trip_plan_create",
    "itinerary_follow_up",
    "live_runtime",
    "unknown",
]


class AssistantTurnContext(BaseModel):
    traveller_id: str | None = Field(default=None, min_length=1)
    planning_session_id: str | None = Field(default=None, min_length=1)
    trip_id: str | None = Field(default=None, min_length=1)


class AssistantOrchestrateRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    context: AssistantTurnContext = Field(default_factory=AssistantTurnContext)
    source_surface: str = Field(default="assistant")
    stream: bool = Field(default=False)


class AssistantIntentClassification(BaseModel):
    intent: AssistantIntent
    confidence: float
    rationale: str
    extracted_destination_a: str | None = None
    extracted_destination_b: str | None = None
    extracted_duration_days: int | None = None


class AssistantOrchestrateResponse(BaseModel):
    classification: AssistantIntentClassification
    route: str
    continuity_context: dict[str, Any] = Field(default_factory=dict)
    payload: dict[str, Any] = Field(default_factory=dict)