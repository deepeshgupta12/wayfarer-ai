from datetime import datetime

from pydantic import BaseModel, Field


class TravellerMemoryCreateRequest(BaseModel):
    traveller_id: str = Field(..., min_length=1)
    event_type: str = Field(..., min_length=1)
    source_surface: str = Field(..., min_length=1)
    payload: dict[str, object] = Field(default_factory=dict)


class TravellerMemoryItem(BaseModel):
    id: int
    traveller_id: str
    event_type: str
    source_surface: str
    payload: dict[str, object]
    created_at: datetime


class TravellerMemoryCreateResponse(TravellerMemoryItem):
    saved: bool = True


class TravellerMemoryListResponse(BaseModel):
    traveller_id: str
    total: int
    items: list[TravellerMemoryItem]