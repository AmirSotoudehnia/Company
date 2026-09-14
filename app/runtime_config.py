from app.db import db


DEFAULTS = {"search_query": "software developer", "search_limit": "25", "search_mode": "auto"}


def get_setting(key: str) -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM runtime_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULTS[key]


def set_search(query: str, limit: int = 25, mode: str = "job_ads") -> dict:
    query = query.strip()
    if not query:
        raise ValueError("Search query is required")
    limit = min(max(int(limit), 1), 100)
    if mode not in {"auto", "job_ads", "local_businesses_without_website", "general_web"}:
        raise ValueError("Unsupported search mode")
    with db() as conn:
        for key, value in (("search_query", query), ("search_limit", str(limit)), ("search_mode", mode)):
            conn.execute(
                """INSERT INTO runtime_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP""",
                (key, value),
            )
    sources = {"job_ads": "arbetsformedlingen_jobtech",
               "local_businesses_without_website": "openstreetmap_missing_website",
               "general_web": "tavily_web_research", "auto": "automatic_router"}
    return {"query": query, "limit": limit, "mode": mode, "source": sources[mode]}


def get_search() -> dict:
    mode = get_setting("search_mode")
    sources = {"job_ads": "arbetsformedlingen_jobtech",
               "local_businesses_without_website": "openstreetmap_missing_website",
               "general_web": "tavily_web_research", "auto": "automatic_router"}
    return {"query": get_setting("search_query"), "limit": int(get_setting("search_limit")),
            "mode": mode, "source": sources.get(mode, "automatic_router")}
