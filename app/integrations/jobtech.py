from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.opportunity_discovery import DiscoveredOpportunity

BASE_URL = "https://jobsearch.api.jobtechdev.se/search"


class JobTechConnector:
    """Official public JobSearch connector for Arbetsförmedlingen/JobTech."""

    def search(self, query: str, limit: int = 25) -> list[DiscoveredOpportunity]:
        query = query.strip()
        if not query:
            raise ValueError("JobTech query is required")
        safe_limit = min(max(int(limit), 1), 100)
        url = f"{BASE_URL}?{urlencode({'q': query, 'limit': safe_limit})}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "AgentCompany/0.6"})
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        return [self._convert(hit) for hit in payload.get("hits", []) if hit.get("headline")]

    @staticmethod
    def _convert(hit: dict) -> DiscoveredOpportunity:
        description = hit.get("description") or {}
        employer = hit.get("employer") or {}
        address = hit.get("workplace_address") or {}
        text = description.get("text") or description.get("text_formatted") or ""
        context = " | ".join(x for x in [employer.get("name", ""), address.get("municipality", "")] if x)
        brief = f"{context}\n{text}".strip()
        return DiscoveredOpportunity(
            title=str(hit["headline"]).strip(),
            brief=brief[:12000],
            source="arbetsformedlingen_jobtech",
            source_url=str(hit.get("webpage_url") or f"https://arbetsformedlingen.se/platsbanken/annonser/{hit.get('id', '')}"),
        )
