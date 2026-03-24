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

    def _looks_like_area_name(self, text: str, destination: str) -> bool:
        value = text.strip()
        lowered = value.lower()
        destination_lower = destination.lower()

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
            "station",
            "airport",
            "restaurant",
            "cafe",
            "bar",
        ]
        if any(keyword in lowered for keyword in blocked_keywords):
            return False

        preferred_area_keywords = [
            "district",
            "neighborhood",
            "quarter",
            "ward",
            "town",
            "old town",
            "downtown",
        ]
        if any(keyword in lowered for keyword in preferred_area_keywords):
            return True

        if destination_lower in lowered and len(value.split()) <= 4:
            return True

        return len(value.split()) <= 3

    def _normalize_area_candidate(self, place: dict[str, Any], destination: str) -> str | None:
        display_name = str(place.get("displayName", {}).get("text", "")).strip()
        address = str(place.get("formattedAddress", "")).strip()

        if display_name and self._looks_like_area_name(display_name, destination):
            return display_name

        if address:
            first_part = address.split(",")[0].strip()
            if first_part and self._looks_like_area_name(first_part, destination):
                return first_part

        return None

    def _extract_suggested_areas(self, payload: dict[str, Any], destination: str) -> list[str]:
        suggestions: list[str] = []
        seen: set[str] = set()

        for place in payload.get("places", []) or []:
            candidate = self._normalize_area_candidate(place, destination)
            if not candidate:
                continue

            normalized_key = candidate.lower()
            if normalized_key in seen:
                continue

            seen.add(normalized_key)
            suggestions.append(candidate)

            if len(suggestions) >= 3:
                break

        return suggestions

    def _live_destination_context(self, destination: str) -> dict[str, object]:
        url = f"{self.settings.google_places_base_url}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_places_api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress",
        }
        body = {
            "textQuery": f"best neighborhoods in {destination}",
            "pageSize": 6,
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        suggested_areas = self._extract_suggested_areas(payload, destination)

        return {
            "suggested_areas": suggested_areas or self._stub_destination_context(destination)["suggested_areas"],
            "freshness_note": "Suggested areas were enriched from Google Places live text search with neighborhood-focused filtering.",
        }

    def get_destination_context(self, destination: str) -> dict[str, object]:
        if not self.settings.google_places_api_key_configured:
            return self._stub_destination_context(destination)

        try:
            return self._live_destination_context(destination)
        except Exception:
            return self._stub_destination_context(destination)