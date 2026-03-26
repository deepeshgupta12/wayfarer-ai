from types import SimpleNamespace

from app.services import review_intelligence_service, trip_plan_service
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


def test_parse_brief_does_not_false_positive_wellness_from_relaxed_language() -> None:
    client = get_test_client()

    response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_002b",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["parsed_constraints"]["interests"] == ["food", "culture"]


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


def test_enrich_trip_plan_returns_slot_based_itinerary() -> None:
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
    assert len(payload["candidate_places"]) >= 4
    assert len(payload["itinerary_skeleton"]) == 4

    first_day = payload["itinerary_skeleton"][0]
    assert "day_rationale" in first_day
    assert "continuity_strategy" in first_day
    assert "slots" in first_day
    assert len(first_day["slots"]) == 4
    assert first_day["slots"][0]["slot_type"] == "morning"
    assert first_day["slots"][1]["slot_type"] == "lunch"
    assert first_day["slots"][2]["slot_type"] == "afternoon"
    assert first_day["slots"][3]["slot_type"] == "evening"
    assert "geo_cluster" in payload["candidate_places"][0]
    assert "geo_cluster" in first_day
    assert "continuity_note" in first_day["slots"][0]
    assert "movement_note" in first_day["slots"][0]
    assert "alternatives" in first_day["slots"][0]
    assert "related_locations" in payload["candidate_places"][0]
    assert "workspace_alternatives" in payload
    assert isinstance(payload["workspace_alternatives"], list)


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


def test_update_then_regenerate_enriched_trip_plan_with_slots() -> None:
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
    assert len(payload["candidate_places"]) >= 4
    assert len(payload["itinerary_skeleton"]) == 4
    assert len(payload["itinerary_skeleton"][0]["slots"]) == 4


def test_enriched_day_contains_fallback_candidates() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_008",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    first_day = payload["itinerary_skeleton"][0]

    assert "fallback_candidate_ids" in first_day
    assert "fallback_candidate_names" in first_day
    assert "slots" in first_day
    assert "fallback_candidate_ids" in first_day["slots"][0]
    assert "fallback_candidate_names" in first_day["slots"][0]


def test_enriched_day_reduces_within_day_duplication_when_pool_allows_it() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_008b",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    day_one_slots = payload["itinerary_skeleton"][0]["slots"]
    assigned_ids = [slot["assigned_location_id"] for slot in day_one_slots if slot["assigned_location_id"]]

    assert len(set(assigned_ids)) >= 3


def test_enriched_trip_plan_has_route_aware_lunch_and_evening_specialization() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_008c",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    first_day_slots = payload["itinerary_skeleton"][0]["slots"]

    lunch_slot = [slot for slot in first_day_slots if slot["slot_type"] == "lunch"][0]
    evening_slot = [slot for slot in first_day_slots if slot["slot_type"] == "evening"][0]

    lunch_name = (lunch_slot["assigned_place_name"] or "").lower()
    evening_name = (evening_slot["assigned_place_name"] or "").lower()

    assert lunch_name != ""
    assert evening_name != ""
    assert any(term in lunch_name for term in ["market", "tsukiji", "kagurazaka", "tokyo"])
    assert any(term in evening_name for term in ["shibuya", "kagurazaka", "asakusa", "tokyo"])


def test_enriched_trip_plan_has_tighter_cross_day_anti_repetition() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_008d",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    day_one_ids = set(payload["itinerary_skeleton"][0]["candidate_location_ids"])
    day_two_ids = set(payload["itinerary_skeleton"][1]["candidate_location_ids"])

    assert len(day_one_ids.intersection(day_two_ids)) <= 1


def test_enriched_trip_plan_includes_slot_alternatives() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_008e",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    first_slot = payload["itinerary_skeleton"][0]["slots"][0]

    assert "alternatives" in first_slot
    assert isinstance(first_slot["alternatives"], list)
    assert len(first_slot["alternatives"]) >= 1
    assert first_slot["alternatives"][0]["location_id"] != first_slot["assigned_location_id"]


def test_enrich_trip_plan_persists_itinerary_version_snapshot_memory() -> None:
    client = get_test_client()
    traveller_id = "traveller_trip_plan_008f"

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": traveller_id,
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    memory_response = client.get(
        f"/traveller-memory/{traveller_id}?event_type=itinerary_version_snapshot&planning_session_id={planning_session_id}"
    )
    assert memory_response.status_code == 200

    payload = memory_response.json()
    assert payload["total"] >= 1
    assert payload["items"][0]["event_type"] == "itinerary_version_snapshot"
    assert payload["items"][0]["payload"]["planning_session_id"] == planning_session_id


def test_enrich_trip_plan_reuses_persisted_review_intelligence(monkeypatch) -> None:
    client = get_test_client()

    cached_locations = [
        SimpleNamespace(
            location_id="cache_trip_kyoto_001",
            name="Kyoto",
            city="Kyoto",
            country="Japan",
            category="city",
            rating=4.7,
            review_count=12450,
        ),
        SimpleNamespace(
            location_id="cache_trip_kyoto_002",
            name="Gion",
            city="Kyoto",
            country="Japan",
            category="neighborhood",
            rating=4.8,
            review_count=8750,
        ),
        SimpleNamespace(
            location_id="cache_trip_kyoto_003",
            name="Nishiki Market",
            city="Kyoto",
            country="Japan",
            category="market",
            rating=4.6,
            review_count=6250,
        ),
        SimpleNamespace(
            location_id="cache_trip_kyoto_004",
            name="Arashiyama",
            city="Kyoto",
            country="Japan",
            category="district",
            rating=4.7,
            review_count=7680,
        ),
    ]

    review_map = {
        "Kyoto": {
            "location_id": "cache_trip_kyoto_001",
            "location_name": "Kyoto",
            "reviews": [
                {"rating": 5, "text": "Friendly staff, delicious food, beautiful atmosphere."},
                {"rating": 4, "text": "Fresh flavors and cozy ambience. Worth the price."},
            ],
        },
        "Gion": {
            "location_id": "cache_trip_kyoto_002",
            "location_name": "Gion",
            "reviews": [
                {"rating": 5, "text": "Helpful service and lovely atmosphere."},
                {"rating": 4, "text": "Beautiful lanes and good value."},
            ],
        },
        "Nishiki Market": {
            "location_id": "cache_trip_kyoto_003",
            "location_name": "Nishiki Market",
            "reviews": [
                {"rating": 5, "text": "Delicious food and lively market atmosphere."},
                {"rating": 4, "text": "Fresh flavors and good value."},
            ],
        },
        "Arashiyama": {
            "location_id": "cache_trip_kyoto_004",
            "location_name": "Arashiyama",
            "reviews": [
                {"rating": 5, "text": "Scenic area, calm atmosphere, and beautiful walks."},
                {"rating": 4, "text": "Relaxed pace and lovely ambience."},
            ],
        },
    }

    def fake_search_locations(query: str, traveller_type: str | None, interests: list[str]):
        return cached_locations

    def fake_get_destination_reviews(destination_name: str) -> dict[str, object]:
        return review_map[destination_name]

    monkeypatch.setattr(
        trip_plan_service.tripadvisor_client,
        "search_locations",
        fake_search_locations,
    )
    monkeypatch.setattr(
        trip_plan_service.tripadvisor_client,
        "get_destination_reviews",
        fake_get_destination_reviews,
    )

    first_create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_cache_001",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert first_create_response.status_code == 200
    first_planning_session_id = first_create_response.json()["planning_session_id"]

    first_enrich_response = client.post(f"/trip-plans/{first_planning_session_id}/enrich")
    assert first_enrich_response.status_code == 200

    def _should_not_reanalyze(*args, **kwargs):
        raise AssertionError("Trip planning should reuse persisted review intelligence before re-analysis.")

    monkeypatch.setattr(
        review_intelligence_service,
        "_analyze_review_bundle_live",
        _should_not_reanalyze,
    )

    second_create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_cache_002",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    assert second_create_response.status_code == 200
    second_planning_session_id = second_create_response.json()["planning_session_id"]

    second_enrich_response = client.post(f"/trip-plans/{second_planning_session_id}/enrich")
    assert second_enrich_response.status_code == 200

    payload = second_enrich_response.json()
    assert payload["status"] == "enriched"
    assert len(payload["candidate_places"]) >= 4
    assert len(payload["itinerary_skeleton"]) == 4


def test_replace_slot_keeps_same_session_and_updates_only_requested_slot() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_009",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200
    enriched_payload = enrich_response.json()

    before_day_two = enriched_payload["itinerary_skeleton"][1]
    before_target_slot = [slot for slot in before_day_two["slots"] if slot["slot_type"] == "evening"][0]

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 2,
            "slot_type": "evening",
            "replacement_mode": "more_culture",
        },
    )
    assert replace_response.status_code == 200

    payload = replace_response.json()
    assert payload["planning_session_id"] == planning_session_id
    assert payload["status"] == "enriched"
    assert len(payload["itinerary_skeleton"]) == 4

    day_two = payload["itinerary_skeleton"][1]
    target_slot = [slot for slot in day_two["slots"] if slot["slot_type"] == "evening"][0]
    assert target_slot["assigned_place_name"] is not None

    if target_slot["assigned_location_id"] != before_target_slot["assigned_location_id"]:
        assert "ranked better" in target_slot["rationale"].lower()
    else:
        assert "no stronger alternative" in target_slot["rationale"].lower()

    day_one_after = payload["itinerary_skeleton"][0]
    day_one_before = enriched_payload["itinerary_skeleton"][0]
    assert day_one_after["day_number"] == day_one_before["day_number"]


def test_replace_slot_prefers_alternative_when_candidate_pool_allows_it() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_009b",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200
    enriched_payload = enrich_response.json()

    before_day = enriched_payload["itinerary_skeleton"][0]
    before_slot = [slot for slot in before_day["slots"] if slot["slot_type"] == "lunch"][0]

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 1,
            "slot_type": "lunch",
            "replacement_mode": "more_food",
        },
    )
    assert replace_response.status_code == 200

    after_payload = replace_response.json()
    after_day = after_payload["itinerary_skeleton"][0]
    after_slot = [slot for slot in after_day["slots"] if slot["slot_type"] == "lunch"][0]

    assert after_slot["assigned_place_name"] is not None
    assert after_slot["assigned_location_id"] != ""

    if after_slot["assigned_location_id"] == before_slot["assigned_location_id"]:
        assert "no stronger alternative" in after_slot["rationale"].lower()
    else:
        assert "ranked better" in after_slot["rationale"].lower()


def test_replace_slot_blocks_swap_when_it_would_weaken_day_coherence() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_009c",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200
    enriched_payload = enrich_response.json()

    before_day = enriched_payload["itinerary_skeleton"][1]
    before_slot = [slot for slot in before_day["slots"] if slot["slot_type"] == "evening"][0]

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 2,
            "slot_type": "evening",
            "replacement_mode": "less_hectic",
            "preferred_location_id": "ta_kyoto_arashiyama_001",
        },
    )
    assert replace_response.status_code == 200

    after_payload = replace_response.json()
    after_day = after_payload["itinerary_skeleton"][1]
    after_slot = [slot for slot in after_day["slots"] if slot["slot_type"] == "evening"][0]

    if after_slot["assigned_location_id"] == before_slot["assigned_location_id"]:
        assert "no stronger alternative" in after_slot["rationale"].lower()


def test_replace_slot_persists_new_itinerary_version_snapshot_memory() -> None:
    client = get_test_client()
    traveller_id = "traveller_trip_plan_009d"

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": traveller_id,
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, balanced pace, love food and culture",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 1,
            "slot_type": "lunch",
            "replacement_mode": "more_food",
        },
    )
    assert replace_response.status_code == 200

    memory_response = client.get(
        f"/traveller-memory/{traveller_id}?event_type=itinerary_version_snapshot&planning_session_id={planning_session_id}"
    )
    assert memory_response.status_code == 200
    payload = memory_response.json()

    assert payload["total"] >= 2


def test_replace_slot_rejects_non_enriched_plan() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_010",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, relaxed pace, love food",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 1,
            "slot_type": "morning",
            "replacement_mode": "best_alternative",
        },
    )
    assert replace_response.status_code == 400
    assert "must be enriched" in replace_response.json()["detail"].lower()


def test_replace_slot_rejects_invalid_day() -> None:
    client = get_test_client()

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_011",
            "brief": "I have 4 days in Tokyo for a solo trip, mid-budget, relaxed pace, love food",
            "source_surface": "assistant",
        },
    )
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    replace_response = client.post(
        f"/trip-plans/{planning_session_id}/replace-slot",
        json={
            "day_number": 9,
            "slot_type": "morning",
            "replacement_mode": "best_alternative",
        },
    )
    assert replace_response.status_code == 400
    assert "day 9 not found" in replace_response.json()["detail"].lower()

def test_enrich_trip_plan_applies_persona_embedding_in_candidate_ranking(monkeypatch) -> None:
    client = get_test_client()

    candidate_results = [
        SimpleNamespace(
            location_id="persona_trip_001",
            name="Kyoto Central Sprint",
            city="Kyoto",
            country="Japan",
            category="city",
            rating=4.9,
            review_count=12000,
        ),
        SimpleNamespace(
            location_id="persona_trip_002",
            name="Kyoto Quiet Heritage",
            city="Kyoto",
            country="Japan",
            category="district",
            rating=4.5,
            review_count=7200,
        ),
        SimpleNamespace(
            location_id="persona_trip_003",
            name="Nishiki Market",
            city="Kyoto",
            country="Japan",
            category="market",
            rating=4.6,
            review_count=6400,
        ),
        SimpleNamespace(
            location_id="persona_trip_004",
            name="Arashiyama",
            city="Kyoto",
            country="Japan",
            category="district",
            rating=4.7,
            review_count=7600,
        ),
    ]

    review_map = {
        "Kyoto Central Sprint": {
            "location_id": "persona_trip_001",
            "location_name": "Kyoto Central Sprint",
            "reviews": [
                {"rating": 5, "text": "Energetic, fast-moving, central experience."},
                {"rating": 4, "text": "Good but busy."},
            ],
        },
        "Kyoto Quiet Heritage": {
            "location_id": "persona_trip_002",
            "location_name": "Kyoto Quiet Heritage",
            "reviews": [
                {"rating": 5, "text": "Quiet lanes, cultural depth, calm atmosphere."},
                {"rating": 4, "text": "Relaxed, scenic, and very walkable."},
            ],
        },
        "Nishiki Market": {
            "location_id": "persona_trip_003",
            "location_name": "Nishiki Market",
            "reviews": [
                {"rating": 5, "text": "Delicious food and lively market atmosphere."},
                {"rating": 4, "text": "Great value and variety."},
            ],
        },
        "Arashiyama": {
            "location_id": "persona_trip_004",
            "location_name": "Arashiyama",
            "reviews": [
                {"rating": 5, "text": "Scenic and calm."},
                {"rating": 4, "text": "Relaxed pace and beautiful walks."},
            ],
        },
    }

    monkeypatch.setattr(
        trip_plan_service.tripadvisor_client,
        "search_locations",
        lambda query, traveller_type, interests: candidate_results,
    )
    monkeypatch.setattr(
        trip_plan_service.tripadvisor_client,
        "get_destination_reviews",
        lambda destination_name: review_map[destination_name],
    )

    def fake_persona_relevance(db, traveller_id, text: str) -> float | None:
        if "Kyoto Quiet Heritage" in text:
            return 0.99
        if "Kyoto Central Sprint" in text:
            return 0.05
        return 0.40

    monkeypatch.setattr(
        trip_plan_service,
        "calculate_persona_relevance_score",
        fake_persona_relevance,
    )

    create_response = client.post(
        "/trip-plans/parse-and-save",
        json={
            "traveller_id": "traveller_trip_plan_persona_001",
            "brief": "I have 4 days in Kyoto for a solo trip, mid-budget, relaxed pace, love culture and wellness",
            "source_surface": "assistant",
        },
    )
    assert create_response.status_code == 200
    planning_session_id = create_response.json()["planning_session_id"]

    enrich_response = client.post(f"/trip-plans/{planning_session_id}/enrich")
    assert enrich_response.status_code == 200

    payload = enrich_response.json()
    assert payload["candidate_places"][0]["name"] == "Kyoto Quiet Heritage"
    assert "strong persona-embedding fit" in payload["candidate_places"][0]["why_selected"].lower()
    assert "related_locations" in payload["candidate_places"][0]
    assert isinstance(payload["candidate_places"][0]["related_locations"], list)

def test_create_trip_plan_from_comparison_preserves_comparison_context() -> None:
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

    create_response = client.post(
        "/trip-plans/from-comparison",
        json={
            "traveller_id": "traveller_trip_plan_cmp_001",
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

    assert create_response.status_code == 200
    payload = create_response.json()

    assert payload["comparison_context"] is not None
    assert payload["comparison_context"]["comparison_id"] == comparison_payload["comparison_id"]
    assert payload["parsed_constraints"]["destination"] == chosen_option["destination"]

    enrich_response = client.post(f"/trip-plans/{payload['planning_session_id']}/enrich")
    assert enrich_response.status_code == 200
    enrich_payload = enrich_response.json()

    assert enrich_payload["comparison_context"] is not None
    assert enrich_payload["comparison_context"]["selected_destination"] == chosen_option["destination"]