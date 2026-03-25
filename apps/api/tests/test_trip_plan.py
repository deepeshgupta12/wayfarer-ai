from tests.conftest import get_test_client


def test_parse_and_save_trip_brief_returns_planning_session() -> None:
    client = get_test_client()

    client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": "traveller_trip_plan_001",
            "travel_style": "midrange",
            "pace_preference": "balanced",
            "group_type": "solo",
            "interests": ["culture", "nature"],
        },
    )

    response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_001",
            "brief": "I have 4 days in Tokyo, mid-budget, love food and calm neighborhoods",
            "source_surface": "assistant",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["traveller_id"] == "traveller_trip_plan_001"
    assert payload["saved"] is True
    assert payload["status"] == "draft"
    assert payload["parsed_constraints"]["destination"] == "Tokyo"
    assert payload["parsed_constraints"]["duration_days"] == 4
    assert payload["parsed_constraints"]["budget"] == "midrange"
    assert "food" in payload["parsed_constraints"]["interests"]
    assert payload["planning_session_id"].startswith("plan_")


def test_parse_and_save_trip_brief_uses_persona_defaults_when_missing() -> None:
    client = get_test_client()

    client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": "traveller_trip_plan_002",
            "travel_style": "luxury",
            "pace_preference": "relaxed",
            "group_type": "couple",
            "interests": ["food", "culture"],
        },
    )

    response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_002",
            "brief": "Plan something in Lisbon for 3 days",
            "source_surface": "assistant",
        },
    )

    assert response.status_code == 200

    payload = response.json()

    assert payload["parsed_constraints"]["destination"] == "Lisbon"
    assert payload["parsed_constraints"]["duration_days"] == 3
    assert payload["parsed_constraints"]["group_type"] == "couple"
    assert payload["parsed_constraints"]["budget"] == "luxury"
    assert payload["parsed_constraints"]["pace_preference"] == "relaxed"
    assert "food" in payload["parsed_constraints"]["interests"]


def test_get_trip_plan_returns_saved_session() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_003",
            "brief": "I want a 5 day Budapest trip for friends with nightlife and food",
            "source_surface": "assistant",
        },
    )

    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    fetch_response = client.get(f"/trip-plans/{planning_session_id}")
    assert fetch_response.status_code == 200

    payload = fetch_response.json()

    assert payload["planning_session_id"] == planning_session_id
    assert payload["traveller_id"] == "traveller_trip_plan_003"
    assert payload["status"] == "draft"
    assert payload["parsed_constraints"]["destination"] == "Budapest"