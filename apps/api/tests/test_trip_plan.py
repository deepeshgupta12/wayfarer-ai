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


def test_enrich_trip_plan_returns_candidates_and_itinerary_skeleton() -> None:
    client = get_test_client()

    client.post(
        "/persona/initialize-and-save",
        json={
            "traveller_id": "traveller_trip_plan_004",
            "travel_style": "midrange",
            "pace_preference": "balanced",
            "group_type": "solo",
            "interests": ["food", "culture"],
        },
    )

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_004",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, love food and calm neighborhoods",
            "source_surface": "assistant",
        },
    )

    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()

    assert payload["planning_session_id"] == planning_session_id
    assert payload["status"] == "enriched"
    assert payload["saved"] is True
    assert len(payload["candidate_places"]) >= 1
    assert len(payload["itinerary_skeleton"]) == 4
    assert payload["candidate_places"][0]["score"] > 0


def test_enrich_trip_plan_rejects_incomplete_sessions() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_005",
            "brief": "Trip to Tokyo",
            "source_surface": "assistant",
        },
    )

    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 400
    assert "Missing fields" in enrich_response.json()["detail"]


def test_update_trip_plan_keeps_same_session_and_clears_old_enrichment() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_006",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, love food and calm neighborhoods",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200
    assert enrich_response.json()["status"] == "enriched"

    update_response = client.patch(
        f"/trip-plans/{planning_session_id}",
        json={
            "pace_preference": "fast",
            "group_type": "couple",
            "interests": ["food", "culture"],
        },
    )
    assert update_response.status_code == 200

    payload = update_response.json()

    assert payload["planning_session_id"] == planning_session_id
    assert payload["status"] == "draft"
    assert payload["parsed_constraints"]["pace_preference"] == "fast"
    assert payload["parsed_constraints"]["group_type"] == "couple"
    assert payload["parsed_constraints"]["interests"] == ["food", "culture"]
    assert payload["candidate_places"] == []
    assert payload["itinerary_skeleton"] == []


def test_update_then_regenerate_enriched_trip_plan() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_007",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, love food and calm neighborhoods",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    update_response = client.patch(
        f"/trip-plans/{planning_session_id}",
        json={
            "pace_preference": "relaxed",
            "group_type": "couple",
            "interests": ["food", "culture"],
        },
    )
    assert update_response.status_code == 200

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()

    assert payload["planning_session_id"] == planning_session_id
    assert payload["status"] == "enriched"
    assert payload["parsed_constraints"]["group_type"] == "couple"
    assert payload["parsed_constraints"]["pace_preference"] == "relaxed"
    assert payload["parsed_constraints"]["interests"] == ["food", "culture"]
    assert len(payload["candidate_places"]) >= 1
    assert len(payload["itinerary_skeleton"]) == 4