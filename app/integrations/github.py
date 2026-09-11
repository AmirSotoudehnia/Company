import os
import httpx

from app.integrations.github_app import provider as github_app_provider

API = "https://api.github.com"


def access_token(installation_id: int | None = None, explicit_token: str | None = None) -> str:
    if explicit_token:
        return explicit_token
    if installation_id:
        return github_app_provider.installation_token(installation_id)
    if github_app_provider.configured():
        return github_app_provider.installation_token()
    token = os.getenv("GITHUB_TOKEN", "")
    if token:
        return token
    raise RuntimeError("GitHub authentication is not configured")


def enabled() -> bool:
    has_repo = bool(os.getenv("GITHUB_OWNER") and os.getenv("GITHUB_REPO"))
    has_auth = bool(os.getenv("GITHUB_TOKEN")) or github_app_provider.configured()
    return has_repo and has_auth


def _headers(installation_id: int | None = None, token: str | None = None) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token(installation_id, token)}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _owner_repo(owner: str | None = None, repo: str | None = None) -> tuple[str, str]:
    owner = owner or os.getenv("GITHUB_OWNER", "")
    repo = repo or os.getenv("GITHUB_REPO", "")
    if not owner or not repo:
        raise RuntimeError("GitHub owner/repository are not configured")
    return owner, repo


def get_issue(issue_number: int, owner: str | None = None, repo: str | None = None, installation_id: int | None = None, token: str | None = None) -> dict:
    owner, repo = _owner_repo(owner, repo)
    with httpx.Client(timeout=20) as client:
        r = client.get(f"{API}/repos/{owner}/{repo}/issues/{issue_number}", headers=_headers(installation_id, token))
        r.raise_for_status()
        return r.json()


def create_pull_request(title: str, body: str, head: str, base: str = "main", owner: str | None = None, repo: str | None = None, installation_id: int | None = None, token: str | None = None) -> dict:
    owner, repo = _owner_repo(owner, repo)
    payload = {"title": title, "body": body, "head": head, "base": base, "draft": True}
    with httpx.Client(timeout=20) as client:
        r = client.post(f"{API}/repos/{owner}/{repo}/pulls", headers=_headers(installation_id, token), json=payload)
        r.raise_for_status()
        return r.json()
