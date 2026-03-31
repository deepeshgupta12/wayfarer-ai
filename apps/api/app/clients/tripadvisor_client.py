from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.core.config import get_settings
from app.schemas.destination import DestinationSearchResult


class TripadvisorClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._cache: dict[str, tuple[float, Any]] = {}
        self._cache_lock = threading.Lock()
        self._inflight_locks: dict[str, threading.Lock] = {}
        self._inflight_lock = threading.Lock()

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
                location_id="ta_tokyo_001",
                name="Tokyo",
                city="Tokyo",
                country="Japan",
                category="city",
                rating=4.8,
                review_count=18420,
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
            DestinationSearchResult(
                location_id="ta_budapest_001",
                name="Budapest",
                city="Budapest",
                country="Hungary",
                category="city",
                rating=4.7,
                review_count=10980,
            ),
        ]

    def _build_destination_stub_catalog(self) -> dict[str, list[DestinationSearchResult]]:
        return {
            "kyoto": [
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
                    location_id="ta_kyoto_gion_001",
                    name="Gion",
                    city="Kyoto",
                    country="Japan",
                    category="neighborhood",
                    rating=4.8,
                    review_count=8750,
                ),
                DestinationSearchResult(
                    location_id="ta_kyoto_higashiyama_001",
                    name="Higashiyama",
                    city="Kyoto",
                    country="Japan",
                    category="district",
                    rating=4.8,
                    review_count=8120,
                ),
                DestinationSearchResult(
                    location_id="ta_kyoto_arashiyama_001",
                    name="Arashiyama",
                    city="Kyoto",
                    country="Japan",
                    category="district",
                    rating=4.7,
                    review_count=7680,
                ),
                DestinationSearchResult(
                    location_id="ta_kyoto_nishiki_001",
                    name="Nishiki Market",
                    city="Kyoto",
                    country="Japan",
                    category="market",
                    rating=4.6,
                    review_count=6250,
                ),
                DestinationSearchResult(
                    location_id="ta_kyoto_pontocho_001",
                    name="Pontocho",
                    city="Kyoto",
                    country="Japan",
                    category="neighborhood",
                    rating=4.6,
                    review_count=5140,
                ),
            ],
            "tokyo": [
                DestinationSearchResult(
                    location_id="ta_tokyo_001",
                    name="Tokyo",
                    city="Tokyo",
                    country="Japan",
                    category="city",
                    rating=4.8,
                    review_count=18420,
                ),
                DestinationSearchResult(
                    location_id="ta_tokyo_asakusa_001",
                    name="Asakusa",
                    city="Tokyo",
                    country="Japan",
                    category="district",
                    rating=4.7,
                    review_count=10240,
                ),
                DestinationSearchResult(
                    location_id="ta_tokyo_shibuya_001",
                    name="Shibuya",
                    city="Tokyo",
                    country="Japan",
                    category="district",
                    rating=4.7,
                    review_count=11120,
                ),
                DestinationSearchResult(
                    location_id="ta_tokyo_ueno_park_001",
                    name="Ueno Park",
                    city="Tokyo",
                    country="Japan",
                    category="park",
                    rating=4.6,
                    review_count=7420,
                ),
                DestinationSearchResult(
                    location_id="ta_tokyo_tsukiji_001",
                    name="Tsukiji Outer Market",
                    city="Tokyo",
                    country="Japan",
                    category="market",
                    rating=4.6,
                    review_count=6890,
                ),
                DestinationSearchResult(
                    location_id="ta_tokyo_kagurazaka_001",
                    name="Kagurazaka",
                    city="Tokyo",
                    country="Japan",
                    category="neighborhood",
                    rating=4.6,
                    review_count=4320,
                ),
            ],
            "lisbon": [
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
                    location_id="ta_lisbon_alfama_001",
                    name="Alfama",
                    city="Lisbon",
                    country="Portugal",
                    category="neighborhood",
                    rating=4.7,
                    review_count=6140,
                ),
                DestinationSearchResult(
                    location_id="ta_lisbon_chiado_001",
                    name="Chiado",
                    city="Lisbon",
                    country="Portugal",
                    category="neighborhood",
                    rating=4.6,
                    review_count=5780,
                ),
                DestinationSearchResult(
                    location_id="ta_lisbon_bairro_alto_001",
                    name="Bairro Alto",
                    city="Lisbon",
                    country="Portugal",
                    category="district",
                    rating=4.6,
                    review_count=5510,
                ),
            ],
            "prague": [
                DestinationSearchResult(
                    location_id="ta_prague_001",
                    name="Prague",
                    city="Prague",
                    country="Czechia",
                    category="city",
                    rating=4.7,
                    review_count=11890,
                ),
                DestinationSearchResult(
                    location_id="ta_prague_old_town_001",
                    name="Old Town",
                    city="Prague",
                    country="Czechia",
                    category="district",
                    rating=4.8,
                    review_count=6680,
                ),
                DestinationSearchResult(
                    location_id="ta_prague_mala_strana_001",
                    name="Mala Strana",
                    city="Prague",
                    country="Czechia",
                    category="district",
                    rating=4.7,
                    review_count=5320,
                ),
                DestinationSearchResult(
                    location_id="ta_prague_vinohrady_001",
                    name="Vinohrady",
                    city="Prague",
                    country="Czechia",
                    category="neighborhood",
                    rating=4.6,
                    review_count=4010,
                ),
            ],
            "budapest": [
                DestinationSearchResult(
                    location_id="ta_budapest_001",
                    name="Budapest",
                    city="Budapest",
                    country="Hungary",
                    category="city",
                    rating=4.7,
                    review_count=10980,
                ),
                DestinationSearchResult(
                    location_id="ta_budapest_castle_001",
                    name="Castle District",
                    city="Budapest",
                    country="Hungary",
                    category="district",
                    rating=4.7,
                    review_count=4980,
                ),
                DestinationSearchResult(
                    location_id="ta_budapest_jewish_quarter_001",
                    name="Jewish Quarter",
                    city="Budapest",
                    country="Hungary",
                    category="district",
                    rating=4.6,
                    review_count=5210,
                ),
                DestinationSearchResult(
                    location_id="ta_budapest_danube_001",
                    name="Danube Promenade",
                    city="Budapest",
                    country="Hungary",
                    category="riverfront",
                    rating=4.6,
                    review_count=4670,
                ),
            ],
        }

    def _stub_reviews(self, destination: str) -> dict[str, object]:
        destination_lower = destination.lower()

        review_map: dict[str, dict[str, object]] = {
            "kyoto": {
                "location_id": "ta_kyoto_001",
                "location_name": "Kyoto",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Beautiful atmosphere, incredibly helpful locals, and rich cultural experiences across the city.",
                    },
                    {
                        "rating": 5,
                        "text": "Food quality was excellent and the historic neighborhoods felt calm, walkable, and worth the time.",
                    },
                    {
                        "rating": 4,
                        "text": "Very strong value for a culture-heavy trip, especially with scenic areas and memorable ambience.",
                    },
                ],
                "source": "stub",
            },
            "gion": {
                "location_id": "ta_kyoto_gion_001",
                "location_name": "Gion",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Atmospheric evening lanes, strong cultural character, and memorable heritage walks.",
                    },
                    {
                        "rating": 4,
                        "text": "Great for couples and culture-focused travellers, especially at a calmer pace.",
                    },
                    {
                        "rating": 4,
                        "text": "Beautiful ambience and a strong sense of place once the busiest stretches thin out.",
                    },
                ],
                "source": "stub",
            },
            "higashiyama": {
                "location_id": "ta_kyoto_higashiyama_001",
                "location_name": "Higashiyama",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Excellent for temples, heritage streets, and slower cultural exploration in Kyoto.",
                    },
                    {
                        "rating": 4,
                        "text": "Walkable, scenic, and especially strong in the morning and afternoon.",
                    },
                    {
                        "rating": 4,
                        "text": "A great fit when history and atmosphere matter more than nightlife.",
                    },
                ],
                "source": "stub",
            },
            "arashiyama": {
                "location_id": "ta_kyoto_arashiyama_001",
                "location_name": "Arashiyama",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Scenic, spacious, and much calmer than central Kyoto with memorable river and bamboo views.",
                    },
                    {
                        "rating": 4,
                        "text": "Very good for relaxed pacing, nature, and slower half-day exploration.",
                    },
                    {
                        "rating": 4,
                        "text": "Worth the time if you want breathing room and a softer rhythm.",
                    },
                ],
                "source": "stub",
            },
            "nishiki market": {
                "location_id": "ta_kyoto_nishiki_001",
                "location_name": "Nishiki Market",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Excellent food variety, memorable local bites, and a fun lunch-focused stop.",
                    },
                    {
                        "rating": 4,
                        "text": "Strong fit for food lovers, though it can feel busy at peak hours.",
                    },
                    {
                        "rating": 4,
                        "text": "Great value for sampling Kyoto cuisine in one compact area.",
                    },
                ],
                "source": "stub",
            },
            "pontocho": {
                "location_id": "ta_kyoto_pontocho_001",
                "location_name": "Pontocho",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Excellent evening ambience, strong dining options, and memorable narrow lanes.",
                    },
                    {
                        "rating": 4,
                        "text": "A strong evening choice for atmosphere, food, and a more romantic city feel.",
                    },
                    {
                        "rating": 4,
                        "text": "Can be lively at night but still feels character-rich and worthwhile.",
                    },
                ],
                "source": "stub",
            },
            "tokyo": {
                "location_id": "ta_tokyo_001",
                "location_name": "Tokyo",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Excellent food scene, efficient service, and so many calm neighborhoods once you get beyond the busiest zones.",
                    },
                    {
                        "rating": 5,
                        "text": "Great value for the depth of experiences, with clean streets, strong ambience, and memorable city energy.",
                    },
                    {
                        "rating": 4,
                        "text": "A huge city, but still easy to shape into a relaxed trip with food-focused exploration.",
                    },
                ],
                "source": "stub",
            },
            "asakusa": {
                "location_id": "ta_tokyo_asakusa_001",
                "location_name": "Asakusa",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Strong heritage atmosphere, temple access, and a good cultural anchor for first-time Tokyo visits.",
                    },
                    {
                        "rating": 4,
                        "text": "Walkable and especially good in the morning before crowds build.",
                    },
                    {
                        "rating": 4,
                        "text": "A nice balance of culture, food streets, and traditional feel.",
                    },
                ],
                "source": "stub",
            },
            "shibuya": {
                "location_id": "ta_tokyo_shibuya_001",
                "location_name": "Shibuya",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "High energy, strong nightlife, and lots of dining and people-watching options.",
                    },
                    {
                        "rating": 4,
                        "text": "Best if you want evening atmosphere and broad city energy.",
                    },
                    {
                        "rating": 4,
                        "text": "Very lively, though it can feel hectic if you want a slower pace.",
                    },
                ],
                "source": "stub",
            },
            "ueno park": {
                "location_id": "ta_tokyo_ueno_park_001",
                "location_name": "Ueno Park",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Good breathing room inside Tokyo, with calmer walking, greenery, and nearby museums.",
                    },
                    {
                        "rating": 4,
                        "text": "Strong fit for relaxed afternoons and balanced city pacing.",
                    },
                    {
                        "rating": 4,
                        "text": "Worth pairing with nearby cultural stops when you want less hectic coverage.",
                    },
                ],
                "source": "stub",
            },
            "tsukiji outer market": {
                "location_id": "ta_tokyo_tsukiji_001",
                "location_name": "Tsukiji Outer Market",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Excellent food quality, memorable bites, and especially strong for lunch or early-day food exploration.",
                    },
                    {
                        "rating": 4,
                        "text": "Very rewarding for food-focused travellers, though it can get crowded.",
                    },
                    {
                        "rating": 4,
                        "text": "A good way to anchor a food-heavy Tokyo day.",
                    },
                ],
                "source": "stub",
            },
            "kagurazaka": {
                "location_id": "ta_tokyo_kagurazaka_001",
                "location_name": "Kagurazaka",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Calmer neighborhood rhythm with strong dining and a more local-feeling atmosphere.",
                    },
                    {
                        "rating": 4,
                        "text": "A good fit when you want food and ambience without the most hectic city energy.",
                    },
                    {
                        "rating": 4,
                        "text": "Walkable and enjoyable for slower evening exploration.",
                    },
                ],
                "source": "stub",
            },
            "lisbon": {
                "location_id": "ta_lisbon_001",
                "location_name": "Lisbon",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Friendly service almost everywhere, great food, and charming neighborhoods with strong ambience.",
                    },
                    {
                        "rating": 4,
                        "text": "Worth the price for couples and food lovers, with lively evenings and scenic viewpoints.",
                    },
                    {
                        "rating": 4,
                        "text": "Good value destination with delicious local cuisine and vibrant atmosphere.",
                    },
                ],
                "source": "stub",
            },
            "prague": {
                "location_id": "ta_prague_001",
                "location_name": "Prague",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Beautiful city with excellent ambience, strong value, and plenty of history to explore.",
                    },
                    {
                        "rating": 4,
                        "text": "Very walkable with scenic districts, memorable service, and worthwhile cultural stops.",
                    },
                    {
                        "rating": 4,
                        "text": "Strong overall experience for couples with cozy atmosphere and solid food options.",
                    },
                ],
                "source": "stub",
            },
            "budapest": {
                "location_id": "ta_budapest_001",
                "location_name": "Budapest",
                "reviews": [
                    {
                        "rating": 5,
                        "text": "Strong nightlife, beautiful river views, and excellent value compared with many other European cities.",
                    },
                    {
                        "rating": 4,
                        "text": "Good food, memorable ambience, and a nice mix of culture and evening energy.",
                    },
                    {
                        "rating": 4,
                        "text": "Great for friends, with lively districts and worthwhile historic landmarks.",
                    },
                ],
                "source": "stub",
            },
        }

        if destination_lower in review_map:
            return review_map[destination_lower]

        return {
            "location_id": f"ta_{destination_lower.replace(' ', '_')}_001",
            "location_name": destination,
            "reviews": [
                {
                    "rating": 4,
                    "text": f"Travellers describe {destination} as enjoyable, with solid atmosphere and worthwhile local exploration.",
                },
                {
                    "rating": 4,
                    "text": f"{destination} offers generally good value with memorable neighborhoods and positive travel experiences.",
                },
                {
                    "rating": 4,
                    "text": f"Visitors report helpful local experiences and a strong sense of place in {destination}.",
                },
            ],
            "source": "stub",
        }

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

    def _get_destination_specific_stub_results(
        self,
        query: str,
    ) -> list[DestinationSearchResult]:
        catalog = self._build_destination_stub_catalog()
        lowered_query = query.lower().strip()

        if lowered_query in catalog:
            return catalog[lowered_query]

        for destination_key, items in catalog.items():
            if lowered_query in destination_key:
                return items
            if any(lowered_query in item.name.lower() for item in items):
                return items

        return self._filter_stub_results(query, self._build_stub_results())

    def _normalized(self, value: str | None) -> str:
        return str(value or "").strip().lower()
    
    def _name_has_lodging_brand(self, name: str) -> bool:
        lodging_keywords = [
            "hotel",
            "hostel",
            "resort",
            "apartment",
            "apartments",
            "inn",
            "guest house",
            "guesthouse",
            "suites",
            "suite",
            "villa",
            "stay",
            "lodge",
            "marriott",
            "hilton",
            "hyatt",
            "ritz",
            "ritz-carlton",
            "four seasons",
            "corinthia",
            "regency",
            "intercontinental",
            "holiday inn",
            "ibis",
            "novotel",
            "westin",
            "sheraton",
        ]
        return any(keyword in name for keyword in lodging_keywords)

    def _name_has_service_noise(self, name: str) -> bool:
        service_keywords = [
            "airport transfer",
            "transfer",
            "taxi",
            "cab",
            "shuttle",
            "chauffeur",
            "car service",
            "car rental",
            "tour",
            "ticket",
            "experience",
            "activity",
            "operator",
            "travel agency",
            "booking",
            "airport",
            "massage",
            "spa",
            "wellness centre",
            "wellness center",
            "beauty salon",
            "clinic",
        ]
        return any(keyword in name for keyword in service_keywords)

    def _build_cache_key(self, namespace: str, payload: dict[str, Any]) -> str:
        return f"{namespace}:{json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(',', ':'))}"

    def _get_cache(self, key: str) -> Any | None:
        now = time.time()
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if expires_at <= now:
                self._cache.pop(key, None)
                return None
            return value

    def _set_cache(self, key: str, ttl_seconds: int, value: Any) -> Any:
        expires_at = time.time() + max(ttl_seconds, 1)
        with self._cache_lock:
            self._cache[key] = (expires_at, value)
        return value

    def _get_inflight_lock(self, key: str) -> threading.Lock:
        with self._inflight_lock:
            lock = self._inflight_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._inflight_locks[key] = lock
            return lock

    def _cache_or_compute(
        self,
        namespace: str,
        payload: dict[str, Any],
        ttl_seconds: int,
        factory: Callable[[], Any],
    ) -> Any:
        key = self._build_cache_key(namespace, payload)
        cached = self._get_cache(key)
        if cached is not None:
            return cached

        lock = self._get_inflight_lock(key)
        with lock:
            cached = self._get_cache(key)
            if cached is not None:
                return cached
            value = factory()
            return self._set_cache(key, ttl_seconds, value)

    def _http_get_json(
        self,
        url: str,
        *,
        params: dict[str, Any],
        ttl_seconds: int,
        cache_namespace: str,
    ) -> dict[str, Any]:
        filtered_params = {key: value for key, value in params.items() if value not in (None, "", [])}

        def _request() -> dict[str, Any]:
            attempts = max(self.settings.tripadvisor_retry_attempts, 1)
            last_error: Exception | None = None

            for attempt in range(attempts):
                try:
                    with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
                        response = client.get(url, params=filtered_params)
                        if response.status_code == 429 or response.status_code >= 500:
                            response.raise_for_status()
                        if response.status_code >= 400:
                            response.raise_for_status()
                        return response.json()
                except Exception as exc:
                    last_error = exc
                    if attempt == attempts - 1:
                        break
                    time.sleep(self.settings.tripadvisor_retry_backoff_seconds * (attempt + 1))

            if last_error is not None:
                raise last_error
            raise RuntimeError("Tripadvisor request failed without a surfaced exception.")

        return self._cache_or_compute(
            cache_namespace,
            {"url": url, "params": filtered_params},
            ttl_seconds,
            _request,
        )

    def _normalize_category_name(self, item: dict[str, Any]) -> str:
        category_name = self._normalized((item.get("category") or {}).get("name"))
        subcategory_names = " ".join(
            self._normalized(subcategory.get("name"))
            for subcategory in list(item.get("subcategory") or [])
            if isinstance(subcategory, dict)
        )
        combined = f"{category_name} {subcategory_names}".strip()

        name = self._normalized(item.get("name"))

        if self._name_has_lodging_brand(name):
            return "hotel"
        if self._name_has_service_noise(name):
            return "service"

        if any(term in combined for term in ["spa", "massage", "wellness"]):
            return "service"
        if "geo" in combined or "municipality" in combined or "city" in combined:
            return "city"
        if "neighborhood" in combined:
            return "neighborhood"
        if "district" in combined:
            return "district"
        if "province" in combined or "region" in combined:
            return "region"
        if "island" in combined:
            return "island"
        if "market" in combined or "market" in name:
            return "market"
        if "park" in combined or "park" in name or "garden" in name:
            return "park"
        if "museum" in combined or "museum" in name:
            return "museum"
        if "temple" in combined or "temple" in name or "shrine" in name:
            return "temple"
        if "restaurant" in combined or "cafe" in combined or "food" in combined:
            return "restaurant"
        if "attraction" in combined:
            return "attraction"
        if "hotel" in combined or "lodging" in combined or "accommodation" in combined:
            return "hotel"
        if "tour" in combined or "activity" in combined or "transport" in combined:
            return "service"

        return "place"

    def _is_service_like_result(self, item: dict[str, Any]) -> bool:
        name = self._normalized(item.get("name"))
        category = self._normalize_category_name(item)
        raw_category = self._normalized((item.get("category") or {}).get("name"))

        blocked_category_keywords = [
            "tour",
            "activity",
            "transport",
            "ticket",
            "hotel",
            "lodging",
            "accommodation",
            "service",
            "airline",
            "car rental",
            "spa",
            "massage",
            "wellness",
        ]

        if category in {"service", "hotel"}:
            return True
        if self._name_has_lodging_brand(name):
            return True
        if self._name_has_service_noise(name):
            return True
        if any(keyword in raw_category for keyword in blocked_category_keywords):
            return True

        return False

    def _is_destination_like_result(
        self,
        item: dict[str, Any],
        query: str,
    ) -> bool:
        if self._is_service_like_result(item):
            return False

        name = self._normalized(item.get("name"))
        category = self._normalize_category_name(item)
        address_obj = item.get("address_obj") or {}
        city = self._normalized(address_obj.get("city") or item.get("city"))
        query_lower = self._normalized(query)

        if not name:
            return False

        if category in {"city", "neighborhood", "district", "region", "island"}:
            return True

        return name == query_lower or city == query_lower

    def _is_exploration_safe_result(
        self,
        item: dict[str, Any],
        query: str,
    ) -> bool:
        if self._is_service_like_result(item):
            return False

        name = self._normalized(item.get("name"))
        query_lower = self._normalized(query)
        category = self._normalize_category_name(item)

        if not name:
            return False

        if category in {"city", "neighborhood", "district", "region", "island", "market", "park", "museum", "temple", "attraction", "restaurant", "place"}:
            return True

        return query_lower in name or name == query_lower

    def _score_live_result(
        self,
        item: dict[str, Any],
        query: str,
    ) -> tuple[int, int, int, float, int]:
        name = self._normalized(item.get("name"))
        address_obj = item.get("address_obj") or {}
        city = self._normalized(address_obj.get("city") or item.get("city"))
        query_lower = self._normalized(query)
        category = self._normalize_category_name(item)

        exact_name = 1 if name == query_lower else 0
        exact_city = 1 if city == query_lower else 0
        destination_like = 1 if self._is_destination_like_result(item, query) else 0
        category_bias = {
            "city": 4,
            "neighborhood": 4,
            "district": 4,
            "region": 3,
            "island": 3,
            "market": 2,
            "park": 2,
            "museum": 2,
            "temple": 2,
            "attraction": 1,
            "restaurant": 1,
            "place": 0,
        }.get(category, 0)
        review_count = int(item.get("num_reviews") or item.get("review_count") or 0)

        return (exact_name, exact_city, destination_like, float(category_bias), review_count)

    def _parse_live_search_results(
        self,
        payload: dict[str, Any],
        query: str,
    ) -> list[DestinationSearchResult]:
        raw_items = payload.get("data", []) or []
        filtered_items = [
            item
            for item in raw_items
            if item.get("name") and item.get("location_id")
        ]

        exploration_safe = [
            item for item in filtered_items if self._is_exploration_safe_result(item, query)
        ]
        candidate_items = exploration_safe or [
            item for item in filtered_items if not self._is_service_like_result(item)
        ]

        candidate_items = sorted(
            candidate_items,
            key=lambda item: self._score_live_result(item, query),
            reverse=True,
        )

        seen_keys: set[str] = set()
        results: list[DestinationSearchResult] = []

        for item in candidate_items:
            name = str(item.get("name") or "").strip()
            location_id = str(item.get("location_id") or "").strip()
            address_obj = item.get("address_obj") or {}
            city = str(address_obj.get("city") or item.get("city") or name or "Unknown").strip()
            country = str(address_obj.get("country") or item.get("country") or "Unknown").strip()
            category = self._normalize_category_name(item)

            dedupe_key = f"{location_id}:{name.lower()}:{city.lower()}:{country.lower()}"
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            results.append(
                DestinationSearchResult(
                    location_id=location_id,
                    name=name,
                    city=city,
                    country=country,
                    category=category,
                    rating=float(item.get("rating") or 4.5),
                    review_count=int(item.get("num_reviews") or item.get("review_count") or 1000),
                )
            )

            if len(results) >= self.settings.tripadvisor_max_search_results:
                break

        return results

    def _live_search_locations(
        self,
        query: str,
    ) -> list[DestinationSearchResult]:
        url = f"{self.settings.tripadvisor_base_url}/location/search"
        payload = self._http_get_json(
            url,
            params={
                "searchQuery": query,
                "key": self.settings.tripadvisor_api_key,
                "language": "en",
            },
            ttl_seconds=self.settings.tripadvisor_search_cache_ttl_seconds,
            cache_namespace="tripadvisor_search_http",
        )
        return self._parse_live_search_results(payload, query)

    def _live_location_reviews(
        self,
        location_id: str,
    ) -> list[dict[str, object]]:
        url = f"{self.settings.tripadvisor_base_url}/location/{location_id}/reviews"
        payload = self._http_get_json(
            url,
            params={
                "key": self.settings.tripadvisor_api_key,
                "language": "en",
            },
            ttl_seconds=self.settings.tripadvisor_reviews_cache_ttl_seconds,
            cache_namespace="tripadvisor_reviews_http",
        )

        reviews: list[dict[str, object]] = []

        for item in payload.get("data", []) or []:
            text = str(item.get("text", "")).strip()
            rating = item.get("rating")

            if not text or rating is None:
                continue

            reviews.append(
                {
                    "rating": float(rating),
                    "text": text,
                }
            )

            if len(reviews) >= self.settings.tripadvisor_max_review_count:
                break

        return reviews

    def get_location_details(
        self,
        location_id: str,
    ) -> dict[str, Any]:
        if not self.settings.tripadvisor_api_key_configured or not location_id:
            return {}

        url = f"{self.settings.tripadvisor_base_url}/location/{location_id}/details"
        try:
            return self._http_get_json(
                url,
                params={
                    "key": self.settings.tripadvisor_api_key,
                    "language": "en",
                },
                ttl_seconds=self.settings.tripadvisor_details_cache_ttl_seconds,
                cache_namespace="tripadvisor_details_http",
            )
        except Exception:
            return {}

    def get_location_photos(
        self,
        location_id: str,
        *,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        if not self.settings.tripadvisor_api_key_configured or not location_id:
            return []

        def _load() -> list[dict[str, Any]]:
            url = f"{self.settings.tripadvisor_base_url}/location/{location_id}/photos"
            payload = self._http_get_json(
                url,
                params={
                    "key": self.settings.tripadvisor_api_key,
                    "language": "en",
                },
                ttl_seconds=self.settings.tripadvisor_photos_cache_ttl_seconds,
                cache_namespace="tripadvisor_photos_http",
            )

            photos: list[dict[str, Any]] = []
            for index, item in enumerate(payload.get("data", []) or [], start=1):
                images = item.get("images") or {}
                preferred_image = (
                    images.get("large")
                    or images.get("original")
                    or images.get("medium")
                    or images.get("small")
                    or {}
                )
                image_url = str(
                    preferred_image.get("url")
                    or item.get("images", {}).get("thumbnail", {}).get("url")
                    or ""
                ).strip()
                if not image_url:
                    continue

                caption = str(item.get("caption") or "").strip() or None
                width = preferred_image.get("width")
                height = preferred_image.get("height")

                photos.append(
                    {
                        "photo_id": str(item.get("id") or item.get("photo_id") or f"ta_photo_{location_id}_{index}"),
                        "location_id": location_id,
                        "image_url": image_url,
                        "source": "tripadvisor",
                        "width": int(width) if width is not None else None,
                        "height": int(height) if height is not None else None,
                        "caption": caption,
                        "tags": [],
                        "scene_type": None,
                        "quality_score": 8.5,
                    }
                )

                if len(photos) >= limit:
                    break

            return photos

        try:
            return self._cache_or_compute(
                "tripadvisor_location_photos",
                {"location_id": location_id, "limit": limit},
                self.settings.tripadvisor_photos_cache_ttl_seconds,
                _load,
            )
        except Exception:
            return []

    def search_nearby_locations(
        self,
        *,
        latitude: float,
        longitude: float,
        query: str | None = None,
        limit: int = 10,
    ) -> list[DestinationSearchResult]:
        if not self.settings.tripadvisor_api_key_configured:
            return []

        def _load() -> list[DestinationSearchResult]:
            url = f"{self.settings.tripadvisor_base_url}/location/nearby_search"
            payload = self._http_get_json(
                url,
                params={
                    "key": self.settings.tripadvisor_api_key,
                    "language": "en",
                    "latLong": f"{latitude},{longitude}",
                    "searchQuery": query,
                },
                ttl_seconds=self.settings.tripadvisor_nearby_cache_ttl_seconds,
                cache_namespace="tripadvisor_nearby_http",
            )
            return self._parse_live_search_results(payload, query or "nearby")[:limit]

        try:
            return self._cache_or_compute(
                "tripadvisor_nearby_results",
                {
                    "latitude": round(latitude, 5),
                    "longitude": round(longitude, 5),
                    "query": query or "",
                    "limit": limit,
                },
                self.settings.tripadvisor_nearby_cache_ttl_seconds,
                _load,
            )
        except Exception:
            return []

    def _merge_live_with_destination_stub_results(
        self,
        query: str,
        live_results: list[DestinationSearchResult],
    ) -> list[DestinationSearchResult]:
        _ = query
        return list(live_results)

    def search_locations(
        self,
        query: str,
        traveller_type: str | None = None,
        interests: list[str] | None = None,
    ) -> list[DestinationSearchResult]:
        _ = traveller_type
        _ = interests or []

        if not self.settings.tripadvisor_api_key_configured:
            return self._get_destination_specific_stub_results(query)

        def _load() -> list[DestinationSearchResult]:
            try:
                live_results = self._live_search_locations(query)
                if live_results:
                    return live_results
                return []
            except Exception:
                return []

        return self._cache_or_compute(
            "tripadvisor_search_results",
            {"query": query.strip().lower()},
            self.settings.tripadvisor_search_cache_ttl_seconds,
            _load,
        )

    def get_destination_reviews(
        self,
        destination: str,
        *,
        location_id: str | None = None,
        category: str | None = None,
    ) -> dict[str, object]:
        stub_bundle = self._stub_reviews(destination)

        if not self.settings.tripadvisor_api_key_configured:
            return stub_bundle

        resolved_location_id = (location_id or "").strip()

        if not resolved_location_id:
            try:
                live_results = self.search_locations(destination)
                if not live_results:
                    return {
                        "location_id": f"live_{destination.strip().lower().replace(' ', '_')}",
                        "location_name": destination,
                        "reviews": [],
                        "source": "live_unavailable",
                    }

                preferred: list[DestinationSearchResult] = []
                for item in live_results:
                    normalized_category = self._normalized(item.category)
                    if normalized_category in {"service", "hotel"}:
                        continue
                    preferred.append(item)

                if not preferred:
                    return {
                        "location_id": f"live_{destination.strip().lower().replace(' ', '_')}",
                        "location_name": destination,
                        "reviews": [],
                        "source": "live_unavailable",
                    }

                if category:
                    category_lower = self._normalized(category)
                    matching_category = [
                        item for item in preferred if self._normalized(item.category) == category_lower
                    ]
                    if matching_category:
                        preferred = matching_category

                resolved_location_id = preferred[0].location_id
                destination = preferred[0].name
            except Exception:
                return {
                    "location_id": f"live_{destination.strip().lower().replace(' ', '_')}",
                    "location_name": destination,
                    "reviews": [],
                    "source": "live_unavailable",
                }

        def _load() -> dict[str, object]:
            try:
                live_reviews = self._live_location_reviews(resolved_location_id)
            except Exception:
                live_reviews = []

            if len(live_reviews) < self.settings.tripadvisor_min_live_reviews:
                return {
                    "location_id": resolved_location_id,
                    "location_name": destination,
                    "reviews": live_reviews,
                    "source": "live_insufficient",
                }

            return {
                "location_id": resolved_location_id,
                "location_name": destination,
                "reviews": live_reviews,
                "source": "live",
            }

        try:
            return self._cache_or_compute(
                "tripadvisor_review_bundle",
                {
                    "destination": destination.strip().lower(),
                    "location_id": resolved_location_id,
                },
                self.settings.tripadvisor_reviews_cache_ttl_seconds,
                _load,
            )
        except Exception:
            return {
                "location_id": resolved_location_id or f"live_{destination.strip().lower().replace(' ', '_')}",
                "location_name": destination,
                "reviews": [],
                "source": "live_unavailable",
            }