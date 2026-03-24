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

    def _extract_suggested_areas(self, payload: dict[str, Any]) -> list[str]:
        suggestions: list[str] = []

        for place in payload.get("places", []) or []:
            address = place.get("formattedAddress") or ""
            short_name = place.get("displayName", {}).get("text")
            if short_name:
                suggestions.append(str(short_name))
            elif address:
                suggestions.append(str(address).split(",")[0])

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
            "textQuery": f"best neighborhoods to stay in {destination}",
            "pageSize": 3,
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        suggested_areas = self._extract_suggested_areas(payload)

        return {
            "suggested_areas": suggested_areas or self._stub_destination_context(destination)["suggested_areas"],
            "freshness_note": "Suggested areas were enriched from Google Places live text search.",
        }

    def get_destination_context(self, destination: str) -> dict[str, object]:
        if not self.settings.google_places_api_key_configured:
            return self._stub_destination_context(destination)

        try:
            return self._live_destination_context(destination)
        except Exception:
            return self._stub_destination_context(destination)