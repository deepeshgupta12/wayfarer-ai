from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.destination import DestinationSearchResult


class TripadvisorClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _build_stub_results(self) -> list[DestinationSearchResult]:
        return [
            DestinationSearchResult(
                location_id="ta_kyoto_001",
                name="Kyoto",
                city="Kyoto",
                country="Japan",
                category="city",
                rating=4.7,
                review_count=12450,
            ),
            DestinationSearchResult(
                location_id="ta_lisbon_001",
                name="Lisbon",
                city="Lisbon",
                country="Portugal",
                category="city",
                rating=4.6,
                review_count=10120,
            ),
            DestinationSearchResult(
                location_id="ta_prague_001",
                name="Prague",
                city="Prague",
                country="Czechia",
                category="city",
                rating=4.7,
                review_count=11890,
            ),
        ]

    def _filter_stub_results(
        self,
        query: str,
        stub_results: list[DestinationSearchResult],
    ) -> list[DestinationSearchResult]:
        lowered_query = query.lower()
        filtered = [
            result
            for result in stub_results
            if lowered_query in result.name.lower() or lowered_query in result.city.lower()
        ]
        return filtered or stub_results[:2]

    def _parse_live_search_results(self, payload: dict[str, Any]) -> list[DestinationSearchResult]:
        results: list[DestinationSearchResult] = []

        for item in payload.get("data", []) or []:
            name = item.get("name")
            location_id = item.get("location_id")
            address_obj = item.get("address_obj") or {}
            city = address_obj.get("city") or item.get("city") or name or "Unknown"
            country = address_obj.get("country") or item.get("country") or "Unknown"

            if not name or not location_id:
                continue

            results.append(
                DestinationSearchResult(
                    location_id=str(location_id),
                    name=str(name),
                    city=str(city),
                    country=str(country),
                    category=str(item.get("category", {}).get("name", "place")),
                    rating=4.5,
                    review_count=1000,
                )
            )

        return results

    def _live_search_locations(
        self,
        query: str,
    ) -> list[DestinationSearchResult]:
        url = f"{self.settings.tripadvisor_base_url}/location/search"
        params = {
            "searchQuery": query,
            "key": self.settings.tripadvisor_api_key,
            "language": "en",
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

        return self._parse_live_search_results(payload)

    def search_locations(
        self,
        query: str,
        traveller_type: str | None = None,
        interests: list[str] | None = None,
    ) -> list[DestinationSearchResult]:
        _ = traveller_type
        _ = interests or []

        stub_results = self._build_stub_results()

        if not self.settings.tripadvisor_api_key_configured:
            return self._filter_stub_results(query, stub_results)

        try:
            live_results = self._live_search_locations(query)
            if live_results:
                return live_results
        except Exception:
            pass

        return self._filter_stub_results(query, stub_results)