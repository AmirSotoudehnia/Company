from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse
from app.sales_pipeline import SalesPipeline

@dataclass(frozen=True)
class DiscoveredOpportunity:
    title: str
    brief: str
    source: str
    source_url: str = ""
    budget: float | None = None

class OpportunityDiscovery:
    """Provider-neutral ingestion layer for real external opportunity connectors."""
    def ingest(self, items: list[DiscoveredOpportunity]):
        results=[]
        for item in items:
            if item.source_url:
                u=urlparse(item.source_url)
                if u.scheme not in {"http","https"} or not u.netloc:
                    continue
            results.append(SalesPipeline().create(item.title,item.brief,item.source,item.source_url,item.budget))
        return results

    def connector_status(self):
        # External sites require their own authorized connector/API. Never scrape behind auth.
        return {"manual": "ready", "public_feed": "ready", "external_accounts": "connector_required"}
