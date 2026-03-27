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
            "title": "Proactive monitoring trip",
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


def test_proactive_monitor_inspect_persists_alerts_and_lists_them() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_proactive_001",
        brief="I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    context_response = client.post(
        "/live-runtime/context",
        json={
            "traveller_id": "traveller_proactive_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "live_runtime",
            "trip_status": "active",
            "intent_hint": "culture",
            "transport_mode": "walk",
            "available_minutes": 45,
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
            "traveller_id": "traveller_proactive_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "action_type": "place_closed",
            "location_id": "ta_kyoto_gion_001",
            "day_number": 1,
            "slot_type": "evening",
            "source_surface": "live_runtime",
            "payload": {
                "name": "Gion",
                "reason": "temporarily closed",
            },
        },
    )
    assert action_response.status_code == 200

    inspect_response = client.post(
        "/live-runtime/monitor/inspect",
        json={
            "traveller_id": "traveller_proactive_001",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "proactive_monitor",
            "current_day_only": False,
            "max_days_to_check": 2,
        },
    )
    assert inspect_response.status_code == 200
    inspect_payload = inspect_response.json()

    assert inspect_payload["trip_id"] == trip["trip_id"]
    assert inspect_payload["generated_count"] >= 1
    assert inspect_payload["open_alert_count"] >= 1
    assert len(inspect_payload["alerts"]) >= 1
    assert inspect_payload["alerts"][0]["status"] == "generated"

    alerts_response = client.get(
        f"/live-runtime/alerts/{trip['trip_id']}",
        params={"status": "generated", "limit": 50},
    )
    assert alerts_response.status_code == 200
    alerts_payload = alerts_response.json()

    assert alerts_payload["trip_id"] == trip["trip_id"]
    assert alerts_payload["total"] >= 1
    assert len(alerts_payload["items"]) >= 1
    assert alerts_payload["items"][0]["status"] == "generated"


def test_proactive_monitor_alert_resolution_writes_back_memory_and_graph_route() -> None:
    client = get_test_client()

    trip = _create_enriched_saved_trip(
        client,
        traveller_id="traveller_proactive_002",
        brief="I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    context_response = client.post(
        "/live-runtime/context",
        json={
            "traveller_id": "traveller_proactive_002",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "live_runtime",
            "trip_status": "active",
            "intent_hint": "food",
            "transport_mode": "walk",
            "available_minutes": 45,
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

    inspect_response = client.post(
        "/live-runtime/monitor/inspect",
        json={
            "traveller_id": "traveller_proactive_002",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "source_surface": "proactive_monitor",
            "current_day_only": False,
            "max_days_to_check": 2,
        },
    )
    assert inspect_response.status_code == 200
    inspect_payload = inspect_response.json()
    assert len(inspect_payload["alerts"]) >= 1

    alert_id = inspect_payload["alerts"][0]["alert_id"]

    resolve_response = client.post(
        f"/live-runtime/alerts/{alert_id}/resolve",
        json={
            "status": "resolved",
            "source_surface": "proactive_monitor",
            "resolution_reason": "traveller accepted fallback",
            "payload": {
                "selected_alternative_id": "fallback_demo_001",
            },
        },
    )
    assert resolve_response.status_code == 200
    resolve_payload = resolve_response.json()

    assert resolve_payload["alert_id"] == alert_id
    assert resolve_payload["status"] == "resolved"
    assert resolve_payload["resolution_payload"]["resolution_reason"] == "traveller accepted fallback"

    memory_response = client.get(
        "/traveller-memory/traveller_proactive_002",
        params={"limit": 20, "event_type": "proactive_alert_resolved"},
    )
    assert memory_response.status_code == 200
    memory_payload = memory_response.json()

    assert memory_payload["total"] >= 1
    assert memory_payload["items"][0]["event_type"] == "proactive_alert_resolved"

    graph_response = client.post(
        "/live-runtime/orchestrate",
        json={
            "traveller_id": "traveller_proactive_002",
            "trip_id": trip["trip_id"],
            "planning_session_id": trip["planning_session_id"],
            "message": "Please monitor my active itinerary for issues and suggest alternatives",
            "source_surface": "live_runtime",
        },
    )
    assert graph_response.status_code == 200
    graph_payload = graph_response.json()

    assert graph_payload["run"]["status"] == "completed"
    assert graph_payload["run"]["routed_agent"] == "proactive_monitor_agent"
    assert graph_payload["run"]["final_output"]["agent"] == "proactive_monitor_agent"
    assert "alerts" in graph_payload["run"]["final_output"]