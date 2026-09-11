from __future__ import annotations

import os
import time
from dataclasses import dataclass
from threading import Lock

import httpx
import jwt

API = "https://api.github.com"


class GitHubAppAuthError(RuntimeError):
    pass


@dataclass
class InstallationToken:
    token: str
    expires_at_epoch: float

    def valid(self) -> bool:
        return bool(self.token) and time.time() < self.expires_at_epoch - 120


class GitHubAppTokenProvider:
    """Issue short-lived tokens for any registered GitHub App installation."""

    def __init__(self):
        self._lock = Lock()
        self._cache: dict[int, InstallationToken] = {}

    @staticmethod
    def configured() -> bool:
        return bool(
            os.getenv("GITHUB_APP_ID")
            and (os.getenv("GITHUB_APP_PRIVATE_KEY") or os.getenv("GITHUB_APP_PRIVATE_KEY_PATH"))
        )

    def _private_key(self) -> str:
        inline = os.getenv("GITHUB_APP_PRIVATE_KEY", "")
        if inline:
            return inline.replace("\\n", "\n")
        path = os.getenv("GITHUB_APP_PRIVATE_KEY_PATH", "")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as handle:
                    return handle.read()
            except OSError as exc:
                raise GitHubAppAuthError(f"Cannot read GitHub App private key: {exc}") from exc
        raise GitHubAppAuthError("GitHub App private key is not configured")

    def _app_jwt(self) -> str:
        app_id = os.getenv("GITHUB_APP_ID", "")
        if not app_id:
            raise GitHubAppAuthError("GITHUB_APP_ID is not configured")
        now = int(time.time())
        return jwt.encode({"iat": now - 30, "exp": now + 540, "iss": app_id}, self._private_key(), algorithm="RS256")

    def installation_token(self, installation_id: int | None = None) -> str:
        if installation_id is None:
            installation_id = int(os.getenv("GITHUB_APP_INSTALLATION_ID", "0"))
        if installation_id <= 0:
            raise GitHubAppAuthError("GitHub App installation id is required")
        with self._lock:
            cached = self._cache.get(installation_id)
            if cached and cached.valid():
                return cached.token
            headers = {
                "Authorization": f"Bearer {self._app_jwt()}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            with httpx.Client(timeout=20) as client:
                response = client.post(f"{API}/app/installations/{installation_id}/access_tokens", headers=headers)
            if response.status_code >= 400:
                raise GitHubAppAuthError(f"GitHub App installation token request failed: {response.status_code}")
            token = response.json().get("token")
            if not token:
                raise GitHubAppAuthError("GitHub did not return an installation token")
            self._cache[installation_id] = InstallationToken(token=token, expires_at_epoch=time.time() + 3000)
            return token


provider = GitHubAppTokenProvider()
