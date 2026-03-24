from app.schemas.persona import TravellerPersonaInput, TravellerPersonaOutput


def _detect_archetype(payload: TravellerPersonaInput) -> str:
    interests = set(payload.interests)

    if payload.travel_style == "luxury" or "luxury" in interests:
        return "luxury seeker"

    if payload.group_type == "family":
        return "family explorer"

    if "food" in interests and "culture" in interests:
        return "food and culture explorer"

    if "adventure" in interests and payload.pace_preference == "fast":
        return "adventure traveller"

    if payload.travel_style == "budget" and payload.group_type == "solo":
        return "budget backpacker"

    if "wellness" in interests and payload.pace_preference == "relaxed":
        return "slow wellness traveller"

    return "comfort-seeking explorer"


def _build_summary(archetype: str, payload: TravellerPersonaInput) -> str:
    interests_text = ", ".join(payload.interests)
    return (
        f"You travel like a {archetype} with a {payload.pace_preference} pace, "
        f"usually in a {payload.group_type} setting, with strong interest in {interests_text}."
    )


def build_initial_persona(payload: TravellerPersonaInput) -> TravellerPersonaOutput:
    archetype = _detect_archetype(payload)

    return TravellerPersonaOutput(
        archetype=archetype,
        summary=_build_summary(archetype, payload),
        signals={
            "travel_style": payload.travel_style,
            "pace_preference": payload.pace_preference,
            "group_type": payload.group_type,
            "interests": payload.interests,
        },
    )