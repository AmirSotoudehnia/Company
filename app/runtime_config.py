from app.db import db


DEFAULTS = {"jobtech_query": "software developer", "jobtech_limit": "25"}


def get_setting(key: str) -> str:
    with db() as conn:
        row = conn.execute("SELECT value FROM runtime_settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else DEFAULTS[key]


def set_search(query: str, limit: int = 25) -> dict:
    query = query.strip()
    if not query:
        raise ValueError("Search query is required")
    limit = min(max(int(limit), 1), 100)
    with db() as conn:
        for key, value in (("jobtech_query", query), ("jobtech_limit", str(limit))):
            conn.execute(
                """INSERT INTO runtime_settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP""",
                (key, value),
            )
    return {"query": query, "limit": limit, "source": "arbetsformedlingen_jobtech"}


def get_search() -> dict:
    return {"query": get_setting("jobtech_query"), "limit": int(get_setting("jobtech_limit")),
            "source": "arbetsformedlingen_jobtech"}
