from typing import Literal

from pydantic import BaseModel, Field


TravelStyle = Literal[
    "budget",
    "midrange",
    "luxury",
]

PacePreference = Literal[
    "relaxed",
    "balanced",
    "fast",
]

GroupType = Literal[
    "solo",
    "couple",
    "family",
    "friends",
]

InterestType = Literal[
    "food",
    "culture",
    "adventure",
    "nature",
    "luxury",
    "nightlife",
    "wellness",
]


class TravellerPersonaInput(BaseModel):
    travel_style: TravelStyle = Field(..., description="Budget preference of the traveller.")
    pace_preference: PacePreference = Field(..., description="Preferred pace of travel.")
    group_type: GroupType = Field(..., description="Primary travel group type.")
    interests: list[InterestType] = Field(
        ...,
        min_length=1,
        description="Top travel interests selected during onboarding.",
    )


class TravellerPersonaOutput(BaseModel):
    archetype: str
    summary: str
    signals: dict[str, object]