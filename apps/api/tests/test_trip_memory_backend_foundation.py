from tests.conftest import get_test_client


def _create_and_enrich_plan(client, traveller_id: str, brief: str) -> dict:
    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": traveller_id,
            "brief": brief,
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    return {
        "planning_session_id": planning_session_id,
        "enriched_payload": enrich_response.json(),
    }


def test_promote_plan_to_saved_trip_creates_initial_backend_version() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_001",
        brief="I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Kyoto backend trip",
            "start_date": "2026-04-10",
            "end_date": "2026-04-13",
            "companions": "solo",
            "status": "planning",
            "source_surface": "planner_modal",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["trip_id"].startswith("trip_")
    assert payload["traveller_id"] == "traveller_saved_trip_001"
    assert payload["planning_session_id"] == result["planning_session_id"]
    assert payload["title"] == "Kyoto backend trip"
    assert payload["current_version_number"] == 1
    assert len(payload["itinerary_skeleton"]) == 4

    versions_response = client.get(f"/trips/{payload['trip_id']}/versions?limit=10")
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()

    assert versions_payload["trip_id"] == payload["trip_id"]
    assert versions_payload["total"] >= 1
    assert versions_payload["items"][0]["version_number"] >= 1


def test_list_saved_trips_returns_backend_saved_trip() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_002",
        brief="I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Tokyo backend trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200

    response = client.get("/trips", params={"traveller_id": "traveller_saved_trip_002", "limit": 10})
    assert response.status_code == 200

    payload = response.json()
    assert payload["traveller_id"] == "traveller_saved_trip_002"
    assert payload["total"] >= 1
    assert payload["items"][0]["title"] == "Tokyo backend trip"


def test_create_trip_version_snapshot_increments_version_counter() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_003",
        brief="I have 4 days in Prague for a couple trip, mid-budget, balanced pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Prague backend trip",
            "companions": "couple",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200
    trip_payload = create_trip_response.json()
    trip_id = trip_payload["trip_id"]

    snapshot_response = client.post(
        f"/trips/{trip_id}/versions",
        json={
            "snapshot_reason": "manual_workspace_snapshot",
        },
    )
    assert snapshot_response.status_code == 200
    snapshot_payload = snapshot_response.json()

    assert snapshot_payload["trip_id"] == trip_id
    assert snapshot_payload["version_number"] == 2
    assert snapshot_payload["snapshot_reason"] == "manual_workspace_snapshot"

    trip_response = client.get(f"/trips/{trip_id}")
    assert trip_response.status_code == 200
    assert trip_response.json()["current_version_number"] == 2


def test_trip_signal_persistence_updates_backend_counts() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_004",
        brief="I have 4 days in Lisbon for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Lisbon backend trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200
    trip_id = create_trip_response.json()["trip_id"]

    selected_response = client.post(
        f"/trips/{trip_id}/signals",
        json={
            "signal_type": "selected_place",
            "location_id": "ta_lisbon_chiado_001",
            "payload": {
                "name": "Chiado",
                "city": "Lisbon",
                "category": "neighborhood",
            },
        },
    )
    assert selected_response.status_code == 200

    skipped_response = client.post(
        f"/trips/{trip_id}/signals",
        json={
            "signal_type": "skipped_recommendation",
            "location_id": "ta_lisbon_bairro_001",
            "payload": {
                "name": "Bairro Alto",
                "city": "Lisbon",
                "category": "neighborhood",
            },
        },
    )
    assert skipped_response.status_code == 200

    replaced_response = client.post(
        f"/trips/{trip_id}/signals",
        json={
            "signal_type": "replaced_slot",
            "location_id": "ta_lisbon_alfama_001",
            "day_number": 2,
            "slot_type": "evening",
            "payload": {
                "name": "Alfama",
                "city": "Lisbon",
                "category": "district",
            },
        },
    )
    assert replaced_response.status_code == 200

    trip_response = client.get(f"/trips/{trip_id}")
    assert trip_response.status_code == 200
    trip_payload = trip_response.json()

    assert trip_payload["selected_places_count"] == 1
    assert trip_payload["skipped_recommendations_count"] == 1
    assert trip_payload["replaced_slots_count"] == 1

    signals_response = client.get(f"/trips/{trip_id}/signals?limit=10")
    assert signals_response.status_code == 200
    signals_payload = signals_response.json()

    assert signals_payload["trip_id"] == trip_id
    assert signals_payload["total"] == 3
    assert len(signals_payload["items"]) == 3

def test_live_gem_actions_update_saved_trip_counts() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_gem_001",
        brief="I have 4 days in Lisbon for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Lisbon gem trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200
    trip_id = create_trip_response.json()["trip_id"]

    saved_response = client.post(
        "/live-runtime/actions",
        json={
            "traveller_id": "traveller_saved_trip_gem_001",
            "trip_id": trip_id,
            "planning_session_id": result["planning_session_id"],
            "action_type": "gem_saved",
            "location_id": "ta_lisbon_alfama_001",
            "source_surface": "live_runtime",
            "payload": {"name": "Alfama"},
        },
    )
    assert saved_response.status_code == 200

    skipped_response = client.post(
        "/live-runtime/actions",
        json={
            "traveller_id": "traveller_saved_trip_gem_001",
            "trip_id": trip_id,
            "planning_session_id": result["planning_session_id"],
            "action_type": "gem_skipped",
            "location_id": "ta_lisbon_bairro_001",
            "source_surface": "live_runtime",
            "payload": {"name": "Bairro Alto"},
        },
    )
    assert skipped_response.status_code == 200

    trip_response = client.get(f"/trips/{trip_id}")
    assert trip_response.status_code == 200
    trip_payload = trip_response.json()

    assert trip_payload["selected_places_count"] == 1
    assert trip_payload["skipped_recommendations_count"] == 1

def test_promoted_saved_trip_exposes_comparison_context() -> None:
    client = get_test_client()

    compare_response = client.post(
        "/destinations/compare",
        json={
            "destination_a": "Kyoto",
            "destination_b": "Tokyo",
            "traveller_type": "solo",
            "interests": ["food", "culture"],
            "pace_preference": "balanced",
            "budget": "midrange",
            "duration_days": 4,
        },
    )
    assert compare_response.status_code == 200
    comparison_payload = compare_response.json()
    chosen_option = next(
        option for option in comparison_payload["plan_start_options"] if option["recommended"] is True
    )

    create_plan_response = client.post(
        "/trip-plans/from-comparison",
        json={
            "traveller_id": "traveller_saved_trip_cmp_001",
            "source_surface": "compare",
            "duration_days": 4,
            "group_type": "solo",
            "interests": ["food", "culture"],
            "pace_preference": "balanced",
            "budget": "midrange",
            "comparison_context": {
                "comparison_id": comparison_payload["comparison_id"],
                "source_surface": "compare",
                "destination_a": comparison_payload["destination_a"]["name"],
                "destination_b": comparison_payload["destination_b"]["name"],
                "selected_branch": chosen_option["branch"],
                "selected_destination": chosen_option["destination"],
                "selected_location_id": chosen_option["location_id"],
                "verdict": comparison_payload["verdict"],
                "planning_recommendation": comparison_payload["planning_recommendation"],
                "options": [
                    {
                        "branch": option["branch"],
                        "location_id": option["location_id"],
                        "destination": option["destination"],
                        "weighted_score": option["weighted_score"],
                        "why_pick_this": "Recommended from comparison result." if option["recommended"] else "Alternate branch from comparison result.",
                    }
                    for option in comparison_payload["plan_start_options"]
                ],
            },
        },
    )
    assert create_plan_response.status_code == 200
    planning_session_id = create_plan_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    promote_response = client.post(
        f"/trips/from-plan/{planning_session_id}",
        json={
            "title": "Comparison-started trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "compare",
        },
    )
    assert promote_response.status_code == 200
    payload = promote_response.json()

    assert payload["comparison_context"] is not None
    assert payload["comparison_context"]["comparison_id"] == comparison_payload["comparison_id"]

    versions_response = client.get(f"/trips/{payload['trip_id']}/versions?limit=10")
    assert versions_response.status_code == 200
    versions_payload = versions_response.json()

    assert versions_payload["items"][0]["comparison_context"] is not None
    assert versions_payload["items"][0]["comparison_context"]["comparison_id"] == comparison_payload["comparison_id"]

def test_current_trip_version_endpoint_returns_tagged_current_version() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_005",
        brief="I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Kyoto current version trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200
    trip_id = create_trip_response.json()["trip_id"]

    snapshot_response = client.post(
        f"/trips/{trip_id}/versions",
        json={
            "snapshot_reason": "workspace_edit_snapshot",
            "branch_label": "main",
        },
    )
    assert snapshot_response.status_code == 200

    current_response = client.get(f"/trips/{trip_id}/versions/current")
    assert current_response.status_code == 200
    payload = current_response.json()

    assert payload["trip_id"] == trip_id
    assert payload["is_current"] is True
    assert payload["version_number"] == 2


def test_restore_trip_version_creates_new_current_version() -> None:
    client = get_test_client()

    result = _create_and_enrich_plan(
        client,
        traveller_id="traveller_saved_trip_006",
        brief="I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
    )

    create_trip_response = client.post(
        f"/trips/from-plan/{result['planning_session_id']}",
        json={
            "title": "Tokyo restore version trip",
            "companions": "solo",
            "status": "planning",
            "source_surface": "assistant",
        },
    )
    assert create_trip_response.status_code == 200
    trip_id = create_trip_response.json()["trip_id"]

    versions_response = client.get(f"/trips/{trip_id}/versions?limit=10")
    assert versions_response.status_code == 200
    original_version = versions_response.json()["items"][0]

    snapshot_response = client.post(
        f"/trips/{trip_id}/versions",
        json={
            "snapshot_reason": "workspace_edit_snapshot",
            "branch_label": "main",
        },
    )
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["version_number"] == 2

    restore_response = client.post(
        f"/trips/{trip_id}/versions/{original_version['version_id']}/restore",
        json={
            "snapshot_reason": "restore_selected_version",
            "branch_label": "main",
        },
    )
    assert restore_response.status_code == 200
    restored_trip = restore_response.json()

    assert restored_trip["trip_id"] == trip_id
    assert restored_trip["current_version_number"] == 3
    assert restored_trip["current_version_id"] is not None

    current_response = client.get(f"/trips/{trip_id}/versions/current")
    assert current_response.status_code == 200
    current_payload = current_response.json()

    assert current_payload["version_number"] == 3
    assert current_payload["is_current"] is True
    assert current_payload["restored_from_version_number"] == 1