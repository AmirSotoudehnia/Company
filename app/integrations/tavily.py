from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.settings import settings


class TavilyConnector:
    endpoint = "https://api.tavily.com/search"

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.api_key = api_key or settings.tavily_api_key
        self.timeout = timeout

    def search(self, query: str, limit: int = 10) -> list[dict]:
        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY is not configured")
        payload = json.dumps({
            "api_key": self.api_key,
            "query": query.strip(),
            "search_depth": "advanced",
            "max_results": min(max(int(limit), 1), 20),
            "include_answer": False,
            "include_raw_content": False,
        }).encode("utf-8")
        request = Request(self.endpoint, data=payload, headers={
            "Content-Type": "application/json", "User-Agent": "MyCompany/0.6",
        }, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise RuntimeError(f"Tavily request failed ({exc.code})") from exc
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError("Tavily search is temporarily unavailable") from exc
        return [item for item in data.get("results", []) if item.get("url")]
