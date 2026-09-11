import os
from dataclasses import dataclass


@dataclass
class Settings:
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_owner: str = os.getenv("GITHUB_OWNER", "")
    github_repo: str = os.getenv("GITHUB_REPO", "")
    workspace_root: str = os.getenv("WORKSPACE_ROOT", "/tmp/agent-company-workspaces")
    test_command: str = os.getenv("TEST_COMMAND", "pytest -q")
    command_timeout_seconds: int = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "180"))
    llm_mode: str = os.getenv("LLM_MODE", "mock")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")


settings = Settings()
