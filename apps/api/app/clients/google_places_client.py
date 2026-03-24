class GooglePlacesClient:
    def get_destination_context(self, destination: str) -> dict[str, object]:
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