from __future__ import annotations

import math
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
            live_context = self._live_destination_context(destination)
            suggested_areas = list(live_context.get("suggested_areas") or [])

            if suggested_areas:
                return live_context

            return {
                "suggested_areas": [],
                "freshness_note": (
                    "Google Places is configured, but no sufficiently strong live neighborhood candidates "
                    "were returned for this destination."
                ),
            }
        except Exception:
            return {
                "suggested_areas": [],
                "freshness_note": (
                    "Google Places live neighborhood enrichment is temporarily unavailable for this destination."
                ),
            }
        
    def _build_stub_nearby_catalog(self) -> dict[str, list[dict[str, object]]]:
        return {
            "kyoto": [
                {
                    "location_id": "ta_kyoto_nishiki_001",
                    "name": "Nishiki Market",
                    "city": "Kyoto",
                    "country": "Japan",
                    "category": "market",
                    "rating": 4.6,
                    "review_count": 6250,
                    "latitude": 35.0050,
                    "longitude": 135.7640,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["food", "local", "lunch"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_kyoto_pontocho_001",
                    "name": "Pontocho",
                    "city": "Kyoto",
                    "country": "Japan",
                    "category": "neighborhood",
                    "rating": 4.6,
                    "review_count": 5140,
                    "latitude": 35.0048,
                    "longitude": 135.7706,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["evening", "food", "ambience"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_kyoto_gion_001",
                    "name": "Gion",
                    "city": "Kyoto",
                    "country": "Japan",
                    "category": "neighborhood",
                    "rating": 4.8,
                    "review_count": 8750,
                    "latitude": 35.0037,
                    "longitude": 135.7788,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["culture", "heritage", "evening"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_kyoto_higashiyama_001",
                    "name": "Higashiyama",
                    "city": "Kyoto",
                    "country": "Japan",
                    "category": "district",
                    "rating": 4.8,
                    "review_count": 8120,
                    "latitude": 34.9965,
                    "longitude": 135.7786,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["culture", "morning", "heritage"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_kyoto_arashiyama_001",
                    "name": "Arashiyama",
                    "city": "Kyoto",
                    "country": "Japan",
                    "category": "district",
                    "rating": 4.7,
                    "review_count": 7680,
                    "latitude": 35.0170,
                    "longitude": 135.6771,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["nature", "scenic", "relaxed"],
                    "source": "google_stub_nearby",
                },
            ],
            "tokyo": [
                {
                    "location_id": "ta_tokyo_tsukiji_001",
                    "name": "Tsukiji Outer Market",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "market",
                    "rating": 4.6,
                    "review_count": 6890,
                    "latitude": 35.6655,
                    "longitude": 139.7708,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["food", "lunch", "local"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_tokyo_kagurazaka_001",
                    "name": "Kagurazaka",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "neighborhood",
                    "rating": 4.6,
                    "review_count": 4320,
                    "latitude": 35.7017,
                    "longitude": 139.7393,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["food", "ambience", "evening"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_tokyo_asakusa_001",
                    "name": "Asakusa",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "district",
                    "rating": 4.7,
                    "review_count": 10240,
                    "latitude": 35.7148,
                    "longitude": 139.7967,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["culture", "heritage", "morning"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_tokyo_ueno_park_001",
                    "name": "Ueno Park",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "park",
                    "rating": 4.6,
                    "review_count": 7420,
                    "latitude": 35.7156,
                    "longitude": 139.7730,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["nature", "relaxed", "afternoon"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_tokyo_shibuya_001",
                    "name": "Shibuya",
                    "city": "Tokyo",
                    "country": "Japan",
                    "category": "district",
                    "rating": 4.7,
                    "review_count": 11120,
                    "latitude": 35.6595,
                    "longitude": 139.7005,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["nightlife", "evening", "energy"],
                    "source": "google_stub_nearby",
                },
            ],
            "lisbon": [
                {
                    "location_id": "ta_lisbon_alfama_001",
                    "name": "Alfama",
                    "city": "Lisbon",
                    "country": "Portugal",
                    "category": "neighborhood",
                    "rating": 4.7,
                    "review_count": 6140,
                    "latitude": 38.7120,
                    "longitude": -9.1308,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["culture", "heritage", "walkable"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_lisbon_chiado_001",
                    "name": "Chiado",
                    "city": "Lisbon",
                    "country": "Portugal",
                    "category": "neighborhood",
                    "rating": 4.6,
                    "review_count": 5780,
                    "latitude": 38.7107,
                    "longitude": -9.1435,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["coffee", "food", "shopping"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_lisbon_bairro_alto_001",
                    "name": "Bairro Alto",
                    "city": "Lisbon",
                    "country": "Portugal",
                    "category": "district",
                    "rating": 4.6,
                    "review_count": 5510,
                    "latitude": 38.7130,
                    "longitude": -9.1455,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["nightlife", "evening", "ambience"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_lisbon_lx_factory_001",
                    "name": "LX Factory",
                    "city": "Lisbon",
                    "country": "Portugal",
                    "category": "creative_district",
                    "rating": 4.5,
                    "review_count": 3280,
                    "latitude": 38.7037,
                    "longitude": -9.1782,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["food", "shopping", "creative"],
                    "source": "google_stub_nearby",
                },
            ],
            "prague": [
                {
                    "location_id": "ta_prague_old_town_001",
                    "name": "Old Town",
                    "city": "Prague",
                    "country": "Czechia",
                    "category": "district",
                    "rating": 4.8,
                    "review_count": 6680,
                    "latitude": 50.0870,
                    "longitude": 14.4208,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["culture", "heritage", "walkable"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_prague_mala_strana_001",
                    "name": "Mala Strana",
                    "city": "Prague",
                    "country": "Czechia",
                    "category": "district",
                    "rating": 4.7,
                    "review_count": 5320,
                    "latitude": 50.0876,
                    "longitude": 14.4042,
                    "price_level": "midrange",
                    "open_now": True,
                    "vibe_tags": ["culture", "scenic", "evening"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_prague_vinohrady_001",
                    "name": "Vinohrady",
                    "city": "Prague",
                    "country": "Czechia",
                    "category": "neighborhood",
                    "rating": 4.6,
                    "review_count": 4010,
                    "latitude": 50.0764,
                    "longitude": 14.4472,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["coffee", "food", "local"],
                    "source": "google_stub_nearby",
                },
                {
                    "location_id": "ta_prague_letna_001",
                    "name": "Letna Park",
                    "city": "Prague",
                    "country": "Czechia",
                    "category": "park",
                    "rating": 4.6,
                    "review_count": 2890,
                    "latitude": 50.0963,
                    "longitude": 14.4237,
                    "price_level": "budget",
                    "open_now": True,
                    "vibe_tags": ["nature", "relaxed", "afternoon"],
                    "source": "google_stub_nearby",
                },
            ],
        }

    def _stub_nearby_places(
        self,
        *,
        latitude: float,
        longitude: float,
        city: str | None,
        query: str | None,
        radius_meters: int,
        limit: int,
        open_now_only: bool,
    ) -> list[dict[str, object]]:
        def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
            radius_earth_m = 6_371_000

            phi1 = math.radians(lat1)
            phi2 = math.radians(lat2)
            delta_phi = math.radians(lat2 - lat1)
            delta_lambda = math.radians(lon2 - lon1)

            a = (
                math.sin(delta_phi / 2) ** 2
                + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
            )
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

            return int(round(radius_earth_m * c))

        catalog = self._build_stub_nearby_catalog()
        city_key = (city or "").strip().lower()

        if city_key and city_key in catalog:
            scoped = list(catalog[city_key])
        else:
            scoped = [item for items in catalog.values() for item in items]

        lowered_query = (query or "").strip().lower()

        if lowered_query:
            filtered: list[dict[str, object]] = []
            for item in scoped:
                text_blob = " ".join(
                    [
                        str(item.get("name") or ""),
                        str(item.get("category") or ""),
                        " ".join(str(tag) for tag in list(item.get("vibe_tags") or [])),
                    ]
                ).lower()

                if any(term in lowered_query for term in ["food", "eat", "lunch", "dinner", "coffee", "cafe"]):
                    if any(term in text_blob for term in ["food", "market", "restaurant", "coffee", "cafe", "dining"]):
                        filtered.append(item)
                        continue

                if any(term in lowered_query for term in ["culture", "heritage", "museum", "history", "temple"]):
                    if any(term in text_blob for term in ["culture", "heritage", "historic", "district", "museum"]):
                        filtered.append(item)
                        continue

                if any(term in lowered_query for term in ["nature", "park", "garden", "scenic"]):
                    if any(term in text_blob for term in ["nature", "park", "garden", "scenic"]):
                        filtered.append(item)
                        continue

                if any(term in lowered_query for term in ["nightlife", "bar", "evening", "late"]):
                    if any(term in text_blob for term in ["nightlife", "bar", "evening", "ambience"]):
                        filtered.append(item)
                        continue

                if lowered_query in text_blob:
                    filtered.append(item)

            if filtered:
                scoped = filtered

        ranked: list[tuple[int, dict[str, object]]] = []
        for item in scoped:
            distance_meters = haversine_meters(
                latitude,
                longitude,
                float(item["latitude"]),
                float(item["longitude"]),
            )

            if distance_meters > radius_meters:
                continue

            if open_now_only and item.get("open_now") is False:
                continue

            ranked.append((distance_meters, item))

        ranked.sort(key=lambda row: row[0])

        return [item for _, item in ranked[:limit]]

    def _parse_live_nearby_places(
        self,
        payload: dict[str, Any],
        *,
        city: str | None,
    ) -> list[dict[str, object]]:
        results: list[dict[str, object]] = []

        for place in payload.get("places", []) or []:
            location = place.get("location") or {}
            display_name = str(place.get("displayName", {}).get("text", "")).strip()
            place_id = str(place.get("id", "")).strip()

            if not display_name or not place_id:
                continue

            results.append(
                {
                    "location_id": place_id,
                    "name": display_name,
                    "city": city or "Unknown",
                    "country": "Unknown",
                    "category": str(place.get("primaryType", "place")),
                    "rating": float(place.get("rating", 4.4)),
                    "review_count": int(place.get("userRatingCount", 0)),
                    "latitude": float(location.get("latitude", 0.0)),
                    "longitude": float(location.get("longitude", 0.0)),
                    "price_level": str(place.get("priceLevel", "")).lower() or None,
                    "open_now": (
                        bool(place.get("currentOpeningHours", {}).get("openNow"))
                        if place.get("currentOpeningHours") is not None
                        else None
                    ),
                    "vibe_tags": [],
                    "source": "google_live_nearby",
                }
            )

        return results

    def _live_nearby_places(
        self,
        *,
        latitude: float,
        longitude: float,
        city: str | None,
        country: str | None,
        query: str | None,
        radius_meters: int,
        limit: int,
        open_now_only: bool,
    ) -> list[dict[str, object]]:
        url = f"{self.settings.google_places_base_url}/places:searchText"
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.settings.google_places_api_key,
            "X-Goog-FieldMask": (
                "places.id,"
                "places.displayName,"
                "places.primaryType,"
                "places.location,"
                "places.rating,"
                "places.userRatingCount,"
                "places.currentOpeningHours,"
                "places.priceLevel"
            ),
        }

        city_text = city or ""
        country_text = f", {country}" if country else ""
        text_query = query or "good places"
        body = {
            "textQuery": f"{text_query} near {city_text}{country_text}".strip(),
            "pageSize": min(limit, 20),
            "locationBias": {
                "circle": {
                    "center": {
                        "latitude": latitude,
                        "longitude": longitude,
                    },
                    "radius": float(radius_meters),
                }
            },
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.post(url, headers=headers, json=body)
            response.raise_for_status()
            payload = response.json()

        parsed = self._parse_live_nearby_places(payload, city=city)
        if open_now_only:
            parsed = [item for item in parsed if item.get("open_now") is not False]
        return parsed[:limit]
    
    def get_place_freshness(
        self,
        *,
        location_id: str | None,
        name: str | None,
        city: str | None,
        country: str | None,
    ) -> dict[str, object]:
        catalog = self._build_stub_nearby_catalog()

        if location_id and "closed" in location_id.lower():
            return {
                "location_id": location_id,
                "name": name,
                "city": city,
                "country": country,
                "operational_status": "temporarily_closed",
                "open_now": False,
                "quality_risk_score": 0.2,
                "quality_flags": [],
                "estimated_visit_minutes": 60,
                "freshness_source": "synthetic_closed_signal",
                "summary": "Recent place freshness indicates the place appears temporarily closed.",
            }

        if not self.settings.google_places_api_key_configured:
            for city_items in catalog.values():
                for item in city_items:
                    if location_id and str(item.get("location_id")) == location_id:
                        quality_flags: list[str] = []
                        quality_risk_score = 0.15

                        vibe_tags = [str(tag).lower() for tag in list(item.get("vibe_tags") or [])]
                        if "nightlife" in vibe_tags:
                            quality_flags.append("peak_time_variability")
                            quality_risk_score = max(quality_risk_score, 0.35)
                        if "market" in str(item.get("category") or "").lower():
                            quality_flags.append("crowd_spike_risk")
                            quality_risk_score = max(quality_risk_score, 0.4)

                        return {
                            "location_id": location_id,
                            "name": item.get("name"),
                            "city": item.get("city"),
                            "country": item.get("country"),
                            "operational_status": "open",
                            "open_now": item.get("open_now"),
                            "quality_risk_score": round(quality_risk_score, 2),
                            "quality_flags": quality_flags,
                            "estimated_visit_minutes": 60 if item.get("category") in {"market", "park"} else 90,
                            "freshness_source": "stub",
                            "summary": "Place freshness was re-evaluated using the current place metadata layer.",
                        }

        return {
            "location_id": location_id,
            "name": name,
            "city": city,
            "country": country,
            "operational_status": "unknown",
            "open_now": None,
            "quality_risk_score": 0.25,
            "quality_flags": ["limited_live_metadata"],
            "estimated_visit_minutes": 90,
            "freshness_source": "fallback",
            "summary": "Only partial freshness metadata is available for this place right now.",
        }

    def _build_stub_place_photo_catalog(self) -> dict[str, list[dict[str, object]]]:
        return {
            "ta_kyoto_001": [
                {
                    "photo_id": "photo_ta_kyoto_001_1",
                    "image_url": "https://images.wayfarer.dev/kyoto/overview_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Historic Kyoto street with lantern-lit atmosphere",
                    "tags": ["culture", "heritage", "street", "outdoor", "ambience"],
                    "scene_type": "culture",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_kyoto_001_2",
                    "image_url": "https://images.wayfarer.dev/kyoto/overview_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Traditional dining lane in Kyoto",
                    "tags": ["food", "culture", "evening", "local", "outdoor"],
                    "scene_type": "food",
                    "quality_score": 8.5,
                },
            ],
            "ta_kyoto_gion_001": [
                {
                    "photo_id": "photo_ta_kyoto_gion_001_1",
                    "image_url": "https://images.wayfarer.dev/kyoto/gion_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Gion evening lane with traditional facades",
                    "tags": ["culture", "heritage", "evening", "ambience", "outdoor"],
                    "scene_type": "culture",
                    "quality_score": 9.1,
                },
                {
                    "photo_id": "photo_ta_kyoto_gion_001_2",
                    "image_url": "https://images.wayfarer.dev/kyoto/gion_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Atmospheric Kyoto neighborhood streetscape",
                    "tags": ["culture", "walkable", "street", "outdoor", "ambience"],
                    "scene_type": "culture",
                    "quality_score": 8.7,
                },
            ],
            "ta_kyoto_higashiyama_001": [
                {
                    "photo_id": "photo_ta_kyoto_higashiyama_001_1",
                    "image_url": "https://images.wayfarer.dev/kyoto/higashiyama_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Temple-lined heritage streets in Higashiyama",
                    "tags": ["culture", "temple", "heritage", "morning", "outdoor"],
                    "scene_type": "culture",
                    "quality_score": 9.0,
                },
                {
                    "photo_id": "photo_ta_kyoto_higashiyama_001_2",
                    "image_url": "https://images.wayfarer.dev/kyoto/higashiyama_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Quiet stone streets and traditional storefronts",
                    "tags": ["culture", "walkable", "heritage", "outdoor", "calm"],
                    "scene_type": "culture",
                    "quality_score": 8.6,
                },
            ],
            "ta_kyoto_arashiyama_001": [
                {
                    "photo_id": "photo_ta_kyoto_arashiyama_001_1",
                    "image_url": "https://images.wayfarer.dev/kyoto/arashiyama_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Scenic riverside and green landscape in Arashiyama",
                    "tags": ["nature", "scenic", "river", "outdoor", "relaxed"],
                    "scene_type": "nature",
                    "quality_score": 9.0,
                },
                {
                    "photo_id": "photo_ta_kyoto_arashiyama_001_2",
                    "image_url": "https://images.wayfarer.dev/kyoto/arashiyama_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Bamboo grove walkway and soft natural light",
                    "tags": ["nature", "bamboo", "walkable", "outdoor", "calm"],
                    "scene_type": "nature",
                    "quality_score": 8.9,
                },
            ],
            "ta_kyoto_nishiki_001": [
                {
                    "photo_id": "photo_ta_kyoto_nishiki_001_1",
                    "image_url": "https://images.wayfarer.dev/kyoto/nishiki_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Food stalls and fresh bites at Nishiki Market",
                    "tags": ["food", "market", "lunch", "local", "indoor"],
                    "scene_type": "food",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_kyoto_nishiki_001_2",
                    "image_url": "https://images.wayfarer.dev/kyoto/nishiki_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Local culinary counters and specialty snacks",
                    "tags": ["food", "local", "market", "indoor", "busy"],
                    "scene_type": "food",
                    "quality_score": 8.4,
                },
            ],
            "ta_tokyo_001": [
                {
                    "photo_id": "photo_ta_tokyo_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/overview_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Tokyo skyline and vibrant urban character",
                    "tags": ["city", "urban", "nightlife", "outdoor", "energy"],
                    "scene_type": "city",
                    "quality_score": 8.7,
                },
                {
                    "photo_id": "photo_ta_tokyo_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/overview_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Tokyo food and cultural mix",
                    "tags": ["food", "culture", "city", "outdoor", "busy"],
                    "scene_type": "city",
                    "quality_score": 8.4,
                },
            ],
            "ta_tokyo_asakusa_001": [
                {
                    "photo_id": "photo_ta_tokyo_asakusa_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/asakusa_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Temple approach and traditional market street in Asakusa",
                    "tags": ["culture", "heritage", "temple", "market", "outdoor"],
                    "scene_type": "culture",
                    "quality_score": 9.0,
                },
                {
                    "photo_id": "photo_ta_tokyo_asakusa_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/asakusa_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Historic Tokyo district streetscape",
                    "tags": ["culture", "walkable", "heritage", "outdoor", "morning"],
                    "scene_type": "culture",
                    "quality_score": 8.6,
                },
            ],
            "ta_tokyo_shibuya_001": [
                {
                    "photo_id": "photo_ta_tokyo_shibuya_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/shibuya_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Shibuya crossing and high-energy city scene",
                    "tags": ["nightlife", "urban", "city", "evening", "outdoor"],
                    "scene_type": "nightlife",
                    "quality_score": 8.9,
                },
                {
                    "photo_id": "photo_ta_tokyo_shibuya_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/shibuya_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Neon-lit dining and nightlife area",
                    "tags": ["nightlife", "food", "evening", "city", "urban"],
                    "scene_type": "nightlife",
                    "quality_score": 8.7,
                },
            ],
            "ta_tokyo_ueno_park_001": [
                {
                    "photo_id": "photo_ta_tokyo_ueno_park_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/ueno_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Green open space and walking paths in Ueno Park",
                    "tags": ["nature", "park", "relaxed", "outdoor", "afternoon"],
                    "scene_type": "nature",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_tokyo_ueno_park_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/ueno_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Museum-side greenery and calm city escape",
                    "tags": ["nature", "culture", "park", "outdoor", "calm"],
                    "scene_type": "nature",
                    "quality_score": 8.4,
                },
            ],
            "ta_tokyo_tsukiji_001": [
                {
                    "photo_id": "photo_ta_tokyo_tsukiji_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/tsukiji_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Fresh seafood counters and packed food lane at Tsukiji",
                    "tags": ["food", "market", "lunch", "local", "busy"],
                    "scene_type": "food",
                    "quality_score": 8.9,
                },
                {
                    "photo_id": "photo_ta_tokyo_tsukiji_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/tsukiji_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Street-food stalls and quick bites in Tokyo market",
                    "tags": ["food", "market", "street", "local", "outdoor"],
                    "scene_type": "food",
                    "quality_score": 8.5,
                },
            ],
            "ta_tokyo_kagurazaka_001": [
                {
                    "photo_id": "photo_ta_tokyo_kagurazaka_001_1",
                    "image_url": "https://images.wayfarer.dev/tokyo/kagurazaka_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Quiet dining street with local neighborhood character",
                    "tags": ["food", "ambience", "walkable", "evening", "outdoor"],
                    "scene_type": "food",
                    "quality_score": 8.7,
                },
                {
                    "photo_id": "photo_ta_tokyo_kagurazaka_001_2",
                    "image_url": "https://images.wayfarer.dev/tokyo/kagurazaka_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Calmer Tokyo lane for slower-paced exploration",
                    "tags": ["culture", "walkable", "calm", "outdoor", "local"],
                    "scene_type": "culture",
                    "quality_score": 8.3,
                },
            ],
            "ta_lisbon_001": [
                {
                    "photo_id": "photo_ta_lisbon_001_1",
                    "image_url": "https://images.wayfarer.dev/lisbon/overview_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Lisbon viewpoints and colorful street texture",
                    "tags": ["city", "culture", "scenic", "outdoor", "walkable"],
                    "scene_type": "city",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_lisbon_001_2",
                    "image_url": "https://images.wayfarer.dev/lisbon/overview_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Food-led city atmosphere in Lisbon",
                    "tags": ["food", "city", "culture", "outdoor", "local"],
                    "scene_type": "city",
                    "quality_score": 8.4,
                },
            ],
            "ta_lisbon_alfama_001": [
                {
                    "photo_id": "photo_ta_lisbon_alfama_001_1",
                    "image_url": "https://images.wayfarer.dev/lisbon/alfama_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Historic lanes and viewpoint charm in Alfama",
                    "tags": ["culture", "heritage", "walkable", "outdoor", "scenic"],
                    "scene_type": "culture",
                    "quality_score": 9.0,
                },
                {
                    "photo_id": "photo_ta_lisbon_alfama_001_2",
                    "image_url": "https://images.wayfarer.dev/lisbon/alfama_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Neighborhood facades and atmospheric walking route",
                    "tags": ["culture", "local", "walkable", "outdoor", "ambience"],
                    "scene_type": "culture",
                    "quality_score": 8.5,
                },
            ],
            "ta_lisbon_chiado_001": [
                {
                    "photo_id": "photo_ta_lisbon_chiado_001_1",
                    "image_url": "https://images.wayfarer.dev/lisbon/chiado_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Cafés, shopping, and central city movement in Chiado",
                    "tags": ["coffee", "food", "shopping", "city", "outdoor"],
                    "scene_type": "food",
                    "quality_score": 8.7,
                },
                {
                    "photo_id": "photo_ta_lisbon_chiado_001_2",
                    "image_url": "https://images.wayfarer.dev/lisbon/chiado_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Elegant streetscape and easy walking routes",
                    "tags": ["city", "walkable", "shopping", "outdoor", "ambience"],
                    "scene_type": "city",
                    "quality_score": 8.3,
                },
            ],
            "ta_lisbon_bairro_alto_001": [
                {
                    "photo_id": "photo_ta_lisbon_bairro_alto_001_1",
                    "image_url": "https://images.wayfarer.dev/lisbon/bairro_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Evening energy and nightlife streets in Bairro Alto",
                    "tags": ["nightlife", "evening", "city", "outdoor", "ambience"],
                    "scene_type": "nightlife",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_lisbon_bairro_alto_001_2",
                    "image_url": "https://images.wayfarer.dev/lisbon/bairro_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Lively bars and street character after dark",
                    "tags": ["nightlife", "bar", "evening", "urban", "outdoor"],
                    "scene_type": "nightlife",
                    "quality_score": 8.5,
                },
            ],
            "ta_prague_001": [
                {
                    "photo_id": "photo_ta_prague_001_1",
                    "image_url": "https://images.wayfarer.dev/prague/overview_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Historic Prague skyline and old-city texture",
                    "tags": ["culture", "heritage", "city", "outdoor", "scenic"],
                    "scene_type": "culture",
                    "quality_score": 8.9,
                },
                {
                    "photo_id": "photo_ta_prague_001_2",
                    "image_url": "https://images.wayfarer.dev/prague/overview_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Walkable city atmosphere and riverfront perspective",
                    "tags": ["city", "walkable", "scenic", "outdoor", "ambience"],
                    "scene_type": "city",
                    "quality_score": 8.4,
                },
            ],
            "ta_prague_old_town_001": [
                {
                    "photo_id": "photo_ta_prague_old_town_001_1",
                    "image_url": "https://images.wayfarer.dev/prague/old_town_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Historic square and Prague old-town architecture",
                    "tags": ["culture", "heritage", "walkable", "outdoor", "city"],
                    "scene_type": "culture",
                    "quality_score": 9.0,
                },
                {
                    "photo_id": "photo_ta_prague_old_town_001_2",
                    "image_url": "https://images.wayfarer.dev/prague/old_town_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Classic Prague streets and landmark facades",
                    "tags": ["culture", "heritage", "city", "outdoor", "ambience"],
                    "scene_type": "culture",
                    "quality_score": 8.6,
                },
            ],
            "ta_prague_mala_strana_001": [
                {
                    "photo_id": "photo_ta_prague_mala_strana_001_1",
                    "image_url": "https://images.wayfarer.dev/prague/mala_strana_1.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Scenic neighborhood view and classic architecture",
                    "tags": ["culture", "scenic", "walkable", "outdoor", "romantic"],
                    "scene_type": "culture",
                    "quality_score": 8.8,
                },
                {
                    "photo_id": "photo_ta_prague_mala_strana_001_2",
                    "image_url": "https://images.wayfarer.dev/prague/mala_strana_2.jpg",
                    "width": 1600,
                    "height": 1067,
                    "caption": "Atmospheric streets for slower-paced exploration",
                    "tags": ["culture", "walkable", "calm", "outdoor", "ambience"],
                    "scene_type": "culture",
                    "quality_score": 8.4,
                },
            ],
        }

    def _stub_place_photos(
        self,
        *,
        location_id: str,
        name: str,
        city: str,
        country: str,
        category: str,
        limit: int,
    ) -> list[dict[str, object]]:
        catalog = self._build_stub_place_photo_catalog()
        if location_id in catalog:
            return list(catalog[location_id][:limit])

        normalized_name = name.lower().replace(" ", "_")
        fallback: list[dict[str, object]] = [
            {
                "photo_id": f"photo_{location_id}_1",
                "image_url": f"https://images.wayfarer.dev/generic/{normalized_name}_1.jpg",
                "width": 1600,
                "height": 1067,
                "caption": f"{name} visual overview",
                "tags": [category.lower(), city.lower(), "travel", "outdoor"],
                "scene_type": "city",
                "quality_score": 8.0,
            },
            {
                "photo_id": f"photo_{location_id}_2",
                "image_url": f"https://images.wayfarer.dev/generic/{normalized_name}_2.jpg",
                "width": 1600,
                "height": 1067,
                "caption": f"{name} local experience view",
                "tags": [category.lower(), "local", "travel", "ambience"],
                "scene_type": "city",
                "quality_score": 7.7,
            },
        ]
        return fallback[:limit]

    def get_place_photos(
        self,
        *,
        location_id: str,
        name: str,
        city: str,
        country: str,
        category: str,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        return self._stub_place_photos(
            location_id=location_id,
            name=name,
            city=city,
            country=country,
            category=category,
            limit=limit,
        )

    def search_nearby_places(
        self,
        *,
        latitude: float,
        longitude: float,
        city: str | None,
        country: str | None = None,
        query: str | None = None,
        radius_meters: int = 800,
        limit: int = 10,
        open_now_only: bool = False,
    ) -> list[dict[str, object]]:
        if not self.settings.google_places_api_key_configured:
            return self._stub_nearby_places(
                latitude=latitude,
                longitude=longitude,
                city=city,
                query=query,
                radius_meters=radius_meters,
                limit=limit,
                open_now_only=open_now_only,
            )

        try:
            live_results = self._live_nearby_places(
                latitude=latitude,
                longitude=longitude,
                city=city,
                country=country,
                query=query,
                radius_meters=radius_meters,
                limit=limit,
                open_now_only=open_now_only,
            )
            if live_results:
                return live_results
        except Exception:
            pass

        return self._stub_nearby_places(
            latitude=latitude,
            longitude=longitude,
            city=city,
            query=query,
            radius_meters=radius_meters,
            limit=limit,
            open_now_only=open_now_only,
        )