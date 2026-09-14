from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.opportunity_discovery import DiscoveredOpportunity

OVERPASS_URL = "http://overpass-api.de/api/interpreter"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
CITY_ALIASES = {"وکخو": "Växjö", "وکسجو": "Växjö", "vaxjo": "Växjö", "växjö": "Växjö"}


class LocalBusinessConnector:
    """Find OSM-listed businesses whose records have no website tag."""

    def search(self, city: str, limit: int = 25) -> list[DiscoveredOpportunity]:
        city = CITY_ALIASES.get(city.strip().lower(), city.strip())
        if not city:
            raise ValueError("City is required")
        safe_limit = min(max(int(limit), 1), 100)
        lat, lon = self._center(city)
        area = f"around:3000,{lat},{lon}"
        query = f"""[out:json][timeout:30];
(
  node({area})["name"]["office"][!"website"][!"contact:website"][!"brand"][!"wikidata"];
  node({area})["name"]["shop"][!"website"][!"contact:website"][!"brand"][!"wikidata"];
  node({area})["name"]["craft"][!"website"][!"contact:website"][!"brand"][!"wikidata"];
);
out center tags {safe_limit};"""
        request = Request(
            OVERPASS_URL,
            data=urlencode({"data": query}).encode(),
            headers={"Accept": "application/json", "User-Agent": "AgentCompany/0.7"},
        )
        last_error = None
        for _ in range(3):
            try:
                with urlopen(request, timeout=45) as response:
                    payload = json.load(response)
                return [self._convert(item, city) for item in payload.get("elements", []) if item.get("tags", {}).get("name")]
            except (HTTPError, URLError, TimeoutError) as exc:
                last_error = exc
        raise RuntimeError(f"Public map service is temporarily unavailable: {last_error}")

    @staticmethod
    def _center(city: str) -> tuple[str, str]:
        url = f"{NOMINATIM_URL}?{urlencode({'q': city + ', Sweden', 'format': 'jsonv2', 'limit': 1})}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "AgentCompany/0.7"})
        with urlopen(request, timeout=20) as response:
            results = json.load(response)
        if not results:
            raise ValueError(f"City not found: {city}")
        return str(results[0]["lat"]), str(results[0]["lon"])

    @staticmethod
    def _convert(item: dict, city: str) -> DiscoveredOpportunity:
        tags = item["tags"]
        kind = tags.get("office") or tags.get("shop") or tags.get("craft") or "business"
        osm_url = f"https://www.openstreetmap.org/{item['type']}/{item['id']}"
        brief = (
            f"Potential local web-design lead in {city}. OSM category: {kind}. "
            "The public map record has no website/contact:website tag. "
            "Verify independently before contacting; absence of a tag does not prove no website exists."
        )
        return DiscoveredOpportunity(
            title=f"{tags['name']} — website verification lead",
            brief=brief,
            source="openstreetmap_missing_website",
            source_url=osm_url,
        )
