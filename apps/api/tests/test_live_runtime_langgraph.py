from tests.conftest import get_test_client


def _create_enriched_saved_trip(client, traveller_id: str, brief: str) -> dict:
    create_plan_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": traveller_id,
            "brief": brief,
            "source_surface": "assistant",
        },
    )
    assert create_plan_response.status_code == 200
    planning_session_id = create_plan_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    promote_response = client.post(
        f"/trips/from-plan/{planning_session_id}",
        json={
            "title": "Live runtime trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert promote_response.status_code == 200

    return {
        "planning_session_id": planning_session_id,
        "trip_id": promote_response.json()["trip_id"],
        "trip_payload": promote_response.json(),
    }


def test_live_context_upsert_and_get_roundtrip() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_ctx_001",
        brief="I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    upsert_response = client.post(
        "/live-runtime/context",
        json={
            "traveller_id": "traveller_live_ctx_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "live_runtime",
            "trip_status": "active",
            "intent_hint": "food",
            "transport_mode": "walk",
            "available_minutes": 90,
            "current_day_number": 1,
            "current_slot_type": "lunch",
            "gps": {
                "latitude": 35.0116,
                "longitude": 135.7681,
                "accuracy_meters": 25,
            },
            "local_time_iso": "2026-04-10T12:30:00+09:00",
            "timezone": "Asia/Tokyo",
            "current_place_name": "Central Kyoto",
            "current_city": "Kyoto",
            "current_country": "Japan",
            "context_payload": {
                "mood": "hungry",
            },
        },
    )
    assert upsert_response.status_code == 200
    upsert_payload = upsert_response.json()

    assert upsert_payload["trip_id"] == trip["trip_id"]
    assert upsert_payload["intent_hint"] == "food"
    assert upsert_payload["transport_mode"] == "walk"
    assert upsert_payload["current_slot_type"] == "lunch"

    get_response = client.get(f"/live-runtime/context/{trip['trip_id']}")
    assert get_response.status_code == 200
    get_payload = get_response.json()

    assert get_payload["trip_id"] == trip["trip_id"]
    assert get_payload["traveller_id"] == "traveller_live_ctx_001"
    assert get_payload["available_minutes"] == 90


def test_live_runtime_orchestrate_routes_nearby_agent_and_persists_run_events() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_run_001",
        brief="I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    context_response = client.post(
        "/live-runtime/context",
        json={
            "traveller_id": "traveller_live_run_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "live_runtime",
            "trip_status": "active",
            "intent_hint": "food",
            "transport_mode": "walk",
            "available_minutes": 60,
            "current_day_number": 1,
            "current_slot_type": "lunch",
            "gps": {
                "latitude": 35.6764,
                "longitude": 139.6500,
                "accuracy_meters": 30,
            },
            "local_time_iso": "2026-04-11T12:15:00+09:00",
            "timezone": "Asia/Tokyo",
            "current_place_name": "Central Tokyo",
            "current_city": "Tokyo",
            "current_country": "Japan",
            "context_payload": {},
        },
    )
    assert context_response.status_code == 200

    response = client.post(
        "/live-runtime/orchestrate",
        json={
            "traveller_id": "traveller_live_run_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "message": "Show me something great nearby right now",
            "source_surface": "live_runtime",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["run"]["run_id"].startswith("live_run_")
    assert payload["run"]["status"] == "completed"
    assert payload["run"]["routed_agent"] == "nearby_agent"
    assert payload["run"]["final_output"]["agent"] == "nearby_agent"
    assert len(payload["run"]["final_output"]["recommendations"]) >= 1

    run_id = payload["run"]["run_id"]

    run_response = client.get(f"/live-runtime/runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["run_id"] == run_id

    events_response = client.get(f"/live-runtime/runs/{run_id}/events?limit=50")
    assert events_response.status_code == 200
    events_payload = events_response.json()

    assert events_payload["run_id"] == run_id
    assert events_payload["total"] >= 3
    node_names = [item["node_name"] for item in events_payload["items"]]
    assert "bootstrap" in node_names
    assert "supervisor" in node_names
    assert "nearby_agent" in node_names


def test_live_runtime_orchestrate_routes_gem_agent() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_gem_001",
        brief="I have 4 days in Lisbon for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    response = client.post(
        "/live-runtime/orchestrate",
        json={
            "traveller_id": "traveller_live_gem_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "message": "What underrated place in this area fits my vibe?",
            "source_surface": "live_runtime",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["run"]["status"] == "completed"
    assert payload["run"]["routed_agent"] == "gem_agent"
    assert payload["run"]["final_output"]["agent"] == "gem_agent"
    assert len(payload["run"]["final_output"]["gems"]) >= 1


def test_live_action_writeback_persists_trip_signal_and_traveller_memory() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_action_001",
        brief="I have 4 days in Prague for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    action_response = client.post(
        "/live-runtime/actions",
        json={
            "traveller_id": "traveller_live_action_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "action_type": "place_closed",
            "location_id": "ta_prague_old_town_001",
            "day_number": 1,
            "slot_type": "evening",
            "source_surface": "live_runtime",
            "payload": {
                "name": "Old Town",
                "reason": "temporarily closed",
            },
        },
    )
    assert action_response.status_code == 200
    action_payload = action_response.json()

    assert action_payload["trip_id"] == trip["trip_id"]
    assert action_payload["action_type"] == "place_closed"
    assert action_payload["memory_event_type"] == "live_place_closed"

    signals_response = client.get(f"/trips/{trip['trip_id']}/signals?limit=10")
    assert signals_response.status_code == 200
    signals_payload = signals_response.json()

    assert signals_payload["total"] >= 1
    assert signals_payload["items"][0]["signal_type"] == "place_closed"

    memory_response = client.get(
        "/traveller-memory/traveller_live_action_001",
        params={"limit": 20, "event_type": "live_place_closed"},
    )
    assert memory_response.status_code == 200
    memory_payload = memory_response.json()

    assert memory_payload["total"] >= 1
    assert memory_payload["items"][0]["event_type"] == "live_place_closed"


def test_live_runtime_replan_agent_uses_recent_live_blocker_signal() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_replan_001",
        brief="I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    context_response = client.post(
        "/live-runtime/context",
        json={
            "traveller_id": "traveller_live_replan_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "live_runtime",
            "trip_status": "active",
            "intent_hint": "culture",
            "transport_mode": "walk",
            "available_minutes": 75,
            "current_day_number": 1,
            "current_slot_type": "evening",
            "gps": {
                "latitude": 35.0116,
                "longitude": 135.7681,
                "accuracy_meters": 25,
            },
            "local_time_iso": "2026-04-10T18:30:00+09:00",
            "timezone": "Asia/Tokyo",
            "current_place_name": "Kyoto center",
            "current_city": "Kyoto",
            "current_country": "Japan",
            "context_payload": {},
        },
    )
    assert context_response.status_code == 200

    action_response = client.post(
        "/live-runtime/actions",
        json={
            "traveller_id": "traveller_live_replan_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "action_type": "place_closed",
            "location_id": "ta_kyoto_closed_001",
            "day_number": 1,
            "slot_type": "evening",
            "source_surface": "live_runtime",
            "payload": {
                "name": "Closed venue",
            },
        },
    )
    assert action_response.status_code == 200

    response = client.post(
        "/live-runtime/orchestrate",
        json={
            "traveller_id": "traveller_live_replan_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "message": "This place is closed, what is the best alternative within walking distance?",
            "source_surface": "live_runtime",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["run"]["status"] == "completed"
    assert payload["run"]["routed_agent"] == "live_replan_agent"
    assert payload["run"]["final_output"]["agent"] == "live_replan_agent"
    assert len(payload["run"]["final_output"]["alternatives"]) >= 1


def test_live_runtime_stream_returns_graph_updates_and_final() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_live_stream_001",
        brief="I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    response = client.post(
        "/live-runtime/orchestrate/stream",
        json={
            "traveller_id": "traveller_live_stream_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "message": "Show me something great nearby right now",
            "source_surface": "live_runtime",
        },
    )
    assert response.status_code == 200
    body = response.text

    assert '"type": "meta"' in body
    assert '"type": "graph_update"' in body
    assert '"type": "final"' in body