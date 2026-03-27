from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


LiveTransportMode = Literal["walk", "transit", "drive"]
LiveSlotType = Literal["morning", "lunch", "afternoon", "evening"]
LiveActionType = Literal[
    "place_closed",
    "place_unavailable",
    "nearby_rejected",
    "nearby_selected",
    "live_context_updated",
]


class LiveGPSContext(BaseModel):
    latitude: float
    longitude: float
    accuracy_meters: float | None = Field(default=None, ge=0)


class LiveTripContextPatch(BaseModel):
    trip_status: str | None = None
    intent_hint: str | None = None
    transport_mode: LiveTransportMode | None = None
    budget_level_override: str | None = None
    available_minutes: int | None = Field(default=None, ge=1, le=1440)
    current_day_number: int | None = Field(default=None, ge=1, le=30)
    current_slot_type: LiveSlotType | None = None
    gps: LiveGPSContext | None = None
    local_time_iso: str | None = None
    timezone: str | None = None
    current_place_name: str | None = None
    current_city: str | None = None
    current_country: str | None = None
    context_payload: dict[str, Any] | None = None


class LiveTripContextUpsertRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    trip_id: str = Field(..., min_length=1)
    planning_session_id: str | None = Field(default=None, min_length=1)
    source_surface: str = Field(default="live_runtime")
    trip_status: str = Field(default="active")
    intent_hint: str | None = None
    transport_mode: LiveTransportMode | None = None
    budget_level_override: str | None = None
    available_minutes: int | None = Field(default=None, ge=1, le=1440)
    current_day_number: int | None = Field(default=None, ge=1, le=30)
    current_slot_type: LiveSlotType | None = None
    gps: LiveGPSContext | None = None
    local_time_iso: str | None = None
    timezone: str | None = None
    current_place_name: str | None = None
    current_city: str | None = None
    current_country: str | None = None
    context_payload: dict[str, Any] = Field(default_factory=dict)


class LiveTripContextResponse(BaseModel):
    trip_id: str
    traveller_id: str
    planning_session_id: str | None = None
    source_surface: str
    trip_status: str
    intent_hint: str | None = None
    transport_mode: str | None = None
    budget_level_override: str | None = None
    available_minutes: int | None = None
    current_day_number: int | None = None
    current_slot_type: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    accuracy_meters: float | None = None
    local_time_iso: str | None = None
    timezone: str | None = None
    current_place_name: str | None = None
    current_city: str | None = None
    current_country: str | None = None
    context_payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LiveActionWriteRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    trip_id: str = Field(..., min_length=1)
    planning_session_id: str | None = Field(default=None, min_length=1)
    action_type: LiveActionType
    location_id: str | None = None
    day_number: int | None = Field(default=None, ge=1, le=30)
    slot_type: LiveSlotType | None = None
    source_surface: str = Field(default="live_runtime")
    payload: dict[str, Any] = Field(default_factory=dict)


class LiveActionWriteResponse(BaseModel):
    signal_id: str
    trip_id: str
    traveller_id: str
    action_type: str
    memory_event_type: str
    saved: bool = True


class AgentGraphEventResponse(BaseModel):
    event_id: str
    run_id: str
    traveller_id: str
    trip_id: str
    event_type: str
    node_name: str | None = None
    sequence_number: int
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class AgentGraphEventListResponse(BaseModel):
    run_id: str
    total: int
    items: list[AgentGraphEventResponse]


class AgentGraphRunResponse(BaseModel):
    run_id: str
    traveller_id: str
    trip_id: str
    planning_session_id: str | None = None
    source_surface: str
    user_message: str
    status: str
    routed_agent: str | None = None
    supervisor_intent: str | None = None
    checkpoint_thread_id: str
    graph_state: dict[str, Any] = Field(default_factory=dict)
    final_output: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class LiveRuntimeOrchestrateRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    trip_id: str = Field(..., min_length=1)
    planning_session_id: str | None = Field(default=None, min_length=1)
    message: str = Field(..., min_length=1)
    source_surface: str = Field(default="live_runtime")
    context_patch: LiveTripContextPatch | None = None


class LiveRuntimeOrchestrateResponse(BaseModel):
    run: AgentGraphRunResponse
    live_context: LiveTripContextResponse | None = None