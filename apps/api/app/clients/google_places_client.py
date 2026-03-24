from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class GooglePlacesClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _stub_destination_context(self, destination: str) -> dict[str, object]:
        destination_map = {
            "kyoto": {
                "suggested_areas": ["Gion", "Higashiyama", "Arashiyama"],
                "freshness_note": "Opening hours and place metadata should be refreshed from Google Places in live mode.",
            },
            "lisbon": {
                "suggested_areas": ["Alfama", "Bairro Alto", "Chiado"],
                "freshness_note": "Opening hours and crowd-sensitive checks should be refreshed from Google Places in live mode.",
            },
            "prague": {
                "suggested_areas": ["Old Town", "Mala Strana", "Vinohrady"],
                "freshness_note": "Opening hours and route feasibility should be refreshed from Google Places in live mode.",
            },
        }

        return destination_map.get(
            destination.lower(),
            {
                "suggested_areas": ["Central District", "Old Town", "Local High Street"],
                "freshness_note": "Live place freshness should be checked from Google Places.",
            },
        )

    def _is_blocked_area_name(self, text: str) -> bool:
        lowered = text.strip().lower()

        blocked_keywords = [
            "hotel",
            "hostel",
            "inn",
            "resort",
            "apartment",
            "suite",
            "stay",
            "tour",
            "experience",
            "museum",
            "temple",
            "shrine",
            "station",
            "airport",
            "restaurant",
            "cafe",
            "bar",
            "market",
            "mall",
            "park",
            "tower",
            "castle",
            "palace",
            "bridge",
            "zoo",
            "aquarium",
        ]
        return any(keyword in lowered for keyword in blocked_keywords)

    def _score_area_name(self, text: str, destination: str) -> int:
        value = text.strip()
        lowered = value.lower()
        destination_lower = destination.lower()

        if not value or self._is_blocked_area_name(value):
            return -100

        score = 0

        strong_area_keywords = [
            "district",
            "neighborhood",
            "quarter",
            "ward",
            "old town",
            "downtown",
        ]
        medium_area_keywords = [
            "town",
            "village",
            "area",
        ]

        if any(keyword in lowered for keyword in strong_area_keywords):
            score += 10
        if any(keyword in lowered for keyword in medium_area_keywords):
            score += 5

        word_count = len(value.split())
        if 1 <= word_count <= 3:
            score += 4
        elif word_count == 4:
            score += 1
        else:
            score -= 3

        if lowered == destination_lower:
            score -= 6
        elif destination_lower in lowered:
            score += 1

        title_like_bonus = 1 if value[:1].isupper() else 0
        score += title_like_bonus

        return score

    def _normalize_area_candidate(self, place: dict[str, Any], destination: str) -> tuple[str | None, int]:
        display_name = str(place.get("displayName", {}).get("text", "")).strip()
        address = str(place.get("formattedAddress", "")).strip()

        candidates: list[tuple[str, int]] = []

        if display_name:
            score = self._score_area_name(display_name, destination)
            if score > 0:
                candidates.append((display_name, score))

        if address:
            first_part = address.split(",")[0].strip()
            if first_part:
                score = self._score_area_name(first_part, destination)
                if score > 0:
                    candidates.append((first_part, score))

        if not candidates:
            return None, -100

        best_candidate = sorted(candidates, key=lambda item: item[1], reverse=True)[0]
        return best_candidate

    def _extract_suggested_areas(self, payload: dict[str, Any], destination: str) -> list[str]:
        ranked_candidates: list[tuple[str, int]] = []
        seen: set[str] = set()

        for place in payload.get("places", []) or []:
            candidate, score = self._normalize_area_candidate(place, destination)
            if not candidate:
                continue

            normalized_key = candidate.lower()
            if normalized_key in seen:
                continue

            seen.add(normalized_key)
            ranked_candidates.append((candidate, score))

        ranked_candidates = sorted(ranked_candidates, key=lambda item: item[1], reverse=True)
        return [candidate for candidate, _ in ranked_candidates[:3]]

    def _live_destination_context(self, destination: str) -> dict[str, object]:
        url = f"{self.settings.google_places_base_url}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_places_api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress",
        }
        body = {
            "textQuery": f"best neighborhoods in {destination}",
            "pageSize": 8,
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        suggested_areas = self._extract_suggested_areas(payload, destination)

        return {
            "suggested_areas": suggested_areas or self._stub_destination_context(destination)["suggested_areas"],
            "freshness_note": "Suggested areas were enriched from Google Places live text search with area ranking and POI filtering.",
        }

    def get_destination_context(self, destination: str) -> dict[str, object]:
        if not self.settings.google_places_api_key_configured:
            return self._stub_destination_context(destination)

        try:
            return self._live_destination_context(destination)
        except Exception:
            return self._stub_destination_context(destination)