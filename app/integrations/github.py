import os
import httpx

from app.integrations.github_app import provider as github_app_provider

API = "https://api.github.com"


def access_token() -> str:
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


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {access_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _owner_repo() -> tuple[str, str]:
    owner = os.getenv("GITHUB_OWNER", "")
    repo = os.getenv("GITHUB_REPO", "")
    if not owner or not repo:
        raise RuntimeError("GITHUB_OWNER/GITHUB_REPO are not configured")
    return owner, repo


def get_issue(issue_number: int) -> dict:
    owner, repo = _owner_repo()
    with httpx.Client(timeout=20) as client:
        r = client.get(f"{API}/repos/{owner}/{repo}/issues/{issue_number}", headers=_headers())
        r.raise_for_status()
        return r.json()


def create_pull_request(title: str, body: str, head: str, base: str = "main") -> dict:
    owner, repo = _owner_repo()
    payload = {"title": title, "body": body, "head": head, "base": base, "draft": True}
    with httpx.Client(timeout=20) as client:
        r = client.post(f"{API}/repos/{owner}/{repo}/pulls", headers=_headers(), json=payload)
        r.raise_for_status()
        return r.json()
