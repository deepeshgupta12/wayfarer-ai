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

    def _canonical_area_map(self, destination: str) -> dict[str, str]:
        destination_lower = destination.lower()

        if destination_lower == "kyoto":
            return {
                "gion district": "Gion",
                "gion": "Gion",
                "higashiyama district": "Higashiyama",
                "higashiyama ward": "Higashiyama",
                "higashiyama": "Higashiyama",
                "arashiyama district": "Arashiyama",
                "arashiyama": "Arashiyama",
                "downtown kyoto": "Downtown Kyoto",
                "central kyoto": "Downtown Kyoto",
                "kyoto downtown": "Downtown Kyoto",
                "kyoto city downtown": "Downtown Kyoto",
                "pontocho": "Pontocho",
                "pontochō": "Pontocho",
            }

        if destination_lower == "lisbon":
            return {
                "alfama district": "Alfama",
                "alfama": "Alfama",
                "bairro alto": "Bairro Alto",
                "chiado district": "Chiado",
                "chiado": "Chiado",
                "baixa": "Baixa",
                "baixa-chiado": "Baixa/Chiado",
            }

        if destination_lower == "prague":
            return {
                "old town": "Old Town",
                "staré město": "Old Town",
                "mala strana": "Mala Strana",
                "malá strana": "Mala Strana",
                "vinohrady": "Vinohrady",
                "new town": "New Town",
            }

        return {}

    def _country_like_names(self) -> set[str]:
        return {
            "japan",
            "portugal",
            "czechia",
            "czech republic",
            "france",
            "italy",
            "spain",
            "germany",
            "india",
            "usa",
            "united states",
            "united kingdom",
        }

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
            "intersection",
            "crossing",
            "bus stop",
            "platform",
            "terminal",
            "ritz-carlton",
            "four seasons",
            "marriott",
            "hilton",
            "hyatt",
            "forest",
            "garden",
            "bamboo grove",
            "bamboo forest",
            "viewpoint",
            "observatory",
            "river walk",
        ]
        return any(keyword in lowered for keyword in blocked_keywords)

    def _is_country_like_name(self, text: str) -> bool:
        return text.strip().lower() in self._country_like_names()

    def _looks_too_granular(self, text: str, destination: str) -> bool:
        value = text.strip()
        lowered = value.lower()
        destination_lower = destination.lower()

        if len(value) <= 3:
            return True

        granular_suffixes = [
            "cho",
            "machi",
            "dori",
            "street",
            "lane",
            "road",
            "avenue",
            "intersection",
        ]
        if any(lowered.endswith(suffix) for suffix in granular_suffixes):
            return True

        words = value.split()
        if len(words) == 1 and destination_lower not in lowered and len(value) > 12:
            return True

        return False

    def _score_area_name(self, text: str, destination: str) -> int:
        value = text.strip()
        lowered = value.lower()
        destination_lower = destination.lower()

        if not value:
            return -100
        if self._is_country_like_name(value):
            return -100
        if self._is_blocked_area_name(value):
            return -100
        if self._looks_too_granular(value, destination):
            return -40

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
            score -= 4

        if lowered == destination_lower:
            score -= 8
        elif destination_lower in lowered:
            score += 1

        canonical_map = self._canonical_area_map(destination)
        if lowered in canonical_map:
            score += 8

        return score

    def _canonicalize_area_candidate(self, candidate: str, destination: str) -> str:
        canonical_map = self._canonical_area_map(destination)
        lowered = candidate.strip().lower()
        return canonical_map.get(lowered, candidate.strip())

    def _normalize_area_candidate(self, place: dict[str, Any], destination: str) -> tuple[str | None, int]:
        display_name = str(place.get("displayName", {}).get("text", "")).strip()
        address = str(place.get("formattedAddress", "")).strip()

        candidates: list[tuple[str, int]] = []

        if display_name:
            canonical = self._canonicalize_area_candidate(display_name, destination)
            score = self._score_area_name(canonical, destination)
            if score > 0:
                candidates.append((canonical, score))

        if address:
            first_part = address.split(",")[0].strip()
            if first_part:
                canonical = self._canonicalize_area_candidate(first_part, destination)
                score = self._score_area_name(canonical, destination)
                if score > 0:
                    candidates.append((canonical, score))

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

        strong_candidates = [candidate for candidate, score in ranked_candidates if score >= 8]
        medium_candidates = [candidate for candidate, score in ranked_candidates if score >= 4]

        if len(strong_candidates) >= 2:
            return strong_candidates[:3]

        if len(medium_candidates) >= 3:
            return medium_candidates[:3]

        return []

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

        if not suggested_areas:
            return {
                "suggested_areas": self._stub_destination_context(destination)["suggested_areas"],
                "freshness_note": "Live Google Places candidates did not meet minimum area-quality thresholds, so curated destination defaults were used.",
            }

        return {
            "suggested_areas": suggested_areas,
            "freshness_note": "Suggested areas were enriched from Google Places live text search with canonicalization, POI suppression, and area-quality guardrails.",
        }

    def get_destination_context(self, destination: str) -> dict[str, object]:
        if not self.settings.google_places_api_key_configured:
            return self._stub_destination_context(destination)

        try:
            return self._live_destination_context(destination)
        except Exception:
            return self._stub_destination_context(destination)