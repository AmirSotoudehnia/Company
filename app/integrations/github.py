import os
import httpx

API = "https://api.github.com"


def enabled() -> bool:
    return bool(os.getenv("GITHUB_TOKEN") and os.getenv("GITHUB_OWNER") and os.getenv("GITHUB_REPO"))


def _headers() -> dict[str, str]:
    token = os.getenv("GITHUB_TOKEN", "")
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not configured")
    return {
        "Authorization": f"Bearer {token}",
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
