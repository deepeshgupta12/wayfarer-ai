from tests.conftest import get_test_client


def test_assistant_orchestrator_routes_destination_compare() -> None:
    client = get_test_client()

    response = client.post(
        "/assistant/orchestrate",
        json={
            "message": "Compare Kyoto vs Tokyo for 4 days",
            "context": {
                "traveller_id": "traveller_assistant_001",
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["classification"]["intent"] == "destination_compare"
    assert payload["route"] == "destinations.compare"
    assert payload["payload"]["comparison_id"] != ""


def test_assistant_orchestrator_routes_trip_plan_create() -> None:
    client = get_test_client()

    response = client.post(
        "/assistant/orchestrate",
        json={
            "message": "Plan a 4 day Kyoto trip for me with food and culture",
            "context": {
                "traveller_id": "traveller_assistant_002",
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["classification"]["intent"] == "trip_plan_create"
    assert payload["route"] == "trip_plans.parse_and_save"
    assert payload["payload"]["planning_session_id"].startswith("plan_")


def test_assistant_orchestrator_routes_itinerary_follow_up() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_assistant_003",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    response = client.post(
        "/assistant/orchestrate",
        json={
            "message": "Change my itinerary for day 2 evening",
            "context": {
                "traveller_id": "traveller_assistant_003",
                "planning_session_id": planning_session_id,
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["classification"]["intent"] == "itinerary_follow_up"
    assert payload["route"] == "trip_plans.get_summary"
    assert payload["payload"]["planning_session_id"] == planning_session_id


def test_assistant_orchestrator_stream_returns_ndjson() -> None:
    client = get_test_client()

    response = client.post(
        "/assistant/orchestrate/stream",
        json={
            "message": "Give me a Kyoto guide for 3 days",
            "context": {
                "traveller_id": "traveller_assistant_004",
            },
        },
    )
    assert response.status_code == 200
    body = response.text

    assert '"type": "meta"' in body
    assert '"type": "final"' in body or '"type": "content_delta"' in body

def test_assistant_orchestrator_resolves_trip_from_planning_session_for_live_runtime() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_assistant_ctx_001",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    promote_response = client.post(
        f"/trips/from-plan/{planning_session_id}",
        json={
            "title": "Kyoto continuity trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert promote_response.status_code == 200
    trip_id = promote_response.json()["trip_id"]

    response = client.post(
        "/assistant/orchestrate",
        json={
            "message": "Show me something great nearby right now",
            "context": {
                "traveller_id": "traveller_assistant_ctx_001",
                "planning_session_id": planning_session_id,
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["classification"]["intent"] == "live_runtime"
    assert payload["route"] == "live_runtime.orchestrate"
    assert payload["continuity_context"]["trip_id"] == trip_id
    assert payload["continuity_context"]["planning_session_id"] == planning_session_id


def test_assistant_orchestrator_resolves_planning_session_from_trip_for_itinerary_follow_up() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_assistant_ctx_002",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    promote_response = client.post(
        f"/trips/from-plan/{planning_session_id}",
        json={
            "title": "Tokyo continuity trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert promote_response.status_code == 200
    trip_id = promote_response.json()["trip_id"]

    response = client.post(
        "/assistant/orchestrate",
        json={
            "message": "Change my itinerary for day 2 evening",
            "context": {
                "traveller_id": "traveller_assistant_ctx_002",
                "trip_id": trip_id,
            },
        },
    )
    assert response.status_code == 200

    payload = response.json()
    assert payload["classification"]["intent"] == "itinerary_follow_up"
    assert payload["route"] == "trip_plans.get_summary"
    assert payload["continuity_context"]["trip_id"] == trip_id
    assert payload["continuity_context"]["planning_session_id"] == planning_session_id