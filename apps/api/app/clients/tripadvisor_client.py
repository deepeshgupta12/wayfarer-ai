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

    def _is_destination_like_result(
        self,
        item: dict[str, Any],
        query: str,
    ) -> bool:
        name = str(item.get("name", "")).strip().lower()
        category_name = str(item.get("category", {}).get("name", "")).strip().lower()
        address_obj = item.get("address_obj") or {}
        city = str(address_obj.get("city", "")).strip().lower()
        query_lower = query.strip().lower()

        if not name:
            return False

        blocked_keywords = [
            "hotel",
            "tour",
            "experience",
            "bus",
            "samurai",
            "resort",
            "hostel",
            "inn",
            "apartment",
            "museum ticket",
        ]
        if any(keyword in name for keyword in blocked_keywords):
            return False

        preferred_category_keywords = [
            "geographic",
            "municipality",
            "city",
            "neighborhood",
            "district",
            "province",
            "island",
        ]
        if any(keyword in category_name for keyword in preferred_category_keywords):
            return True

        return name == query_lower or city == query_lower

    def _score_live_result(
        self,
        item: dict[str, Any],
        query: str,
    ) -> tuple[int, int]:
        name = str(item.get("name", "")).strip().lower()
        category_name = str(item.get("category", {}).get("name", "")).strip().lower()
        address_obj = item.get("address_obj") or {}
        city = str(address_obj.get("city", "")).strip().lower()
        query_lower = query.strip().lower()

        exact_name = 1 if name == query_lower else 0
        exact_city = 1 if city == query_lower else 0
        geographic_bias = 1 if any(
            keyword in category_name
            for keyword in ["geographic", "municipality", "city", "district", "neighborhood"]
        ) else 0

        return (
            exact_name + exact_city + geographic_bias,
            1 if self._is_destination_like_result(item, query) else 0,
        )

    def _parse_live_search_results(
        self,
        payload: dict[str, Any],
        query: str,
    ) -> list[DestinationSearchResult]:
        raw_items = payload.get("data", []) or []

        filtered_items = [
            item for item in raw_items
            if item.get("name") and item.get("location_id")
        ]

        destination_like_items = [
            item for item in filtered_items
            if self._is_destination_like_result(item, query)
        ]

        candidate_items = destination_like_items or filtered_items
        candidate_items = sorted(
            candidate_items,
            key=lambda item: self._score_live_result(item, query),
            reverse=True,
        )

        results: list[DestinationSearchResult] = []

        for item in candidate_items[:10]:
            name = item.get("name")
            location_id = item.get("location_id")
            address_obj = item.get("address_obj") or {}
            city = address_obj.get("city") or item.get("city") or name or "Unknown"
            country = address_obj.get("country") or item.get("country") or "Unknown"

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

        return self._parse_live_search_results(payload, query)

    def _live_location_reviews(
        self,
        location_id: str,
    ) -> list[dict[str, object]]:
        url = f"{self.settings.tripadvisor_base_url}/location/{location_id}/reviews"
        params = {
            "key": self.settings.tripadvisor_api_key,
            "language": "en",
        }

        with httpx.Client(timeout=self.settings.external_api_timeout_seconds) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            payload = response.json()

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

            if len(reviews) >= 5:
                break

        return reviews

    def _merge_live_with_destination_stub_results(
        self,
        query: str,
        live_results: list[DestinationSearchResult],
    ) -> list[DestinationSearchResult]:
        stub_results = self._get_destination_specific_stub_results(query)
        merged: list[DestinationSearchResult] = []
        seen_ids: set[str] = set()

        for result in live_results + stub_results:
            if result.location_id in seen_ids:
                continue
            seen_ids.add(result.location_id)
            merged.append(result)

        return merged

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

        try:
            live_results = self._live_search_locations(query)
            if live_results:
                if len(live_results) < 4:
                    return self._merge_live_with_destination_stub_results(query, live_results)
                return live_results
        except Exception:
            pass

        return self._get_destination_specific_stub_results(query)

    def get_destination_reviews(
        self,
        destination: str,
    ) -> dict[str, object]:
        stub_bundle = self._stub_reviews(destination)

        if not self.settings.tripadvisor_api_key_configured:
            return stub_bundle

        try:
            live_results = self._live_search_locations(destination)
            if not live_results:
                return stub_bundle

            top_result = live_results[0]
            live_reviews = self._live_location_reviews(top_result.location_id)

            if len(live_reviews) < 2:
                return stub_bundle

            return {
                "location_id": top_result.location_id,
                "location_name": top_result.name,
                "reviews": live_reviews,
                "source": "live",
            }
        except Exception:
            return stub_bundle