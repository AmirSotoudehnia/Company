import os
from dataclasses import dataclass


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    github_token: str = os.getenv("GITHUB_TOKEN", "")
    github_owner: str = os.getenv("GITHUB_OWNER", "")
    github_repo: str = os.getenv("GITHUB_REPO", "")
    github_webhook_secret: str = os.getenv("GITHUB_WEBHOOK_SECRET", "")
    bootstrap_token: str = os.getenv("BOOTSTRAP_TOKEN", "")
    workspace_root: str = os.getenv("WORKSPACE_ROOT", "/tmp/agent-company-workspaces")
    test_command: str = os.getenv("TEST_COMMAND", "python -m pytest -q")
    command_timeout_seconds: int = int(os.getenv("COMMAND_TIMEOUT_SECONDS", "180"))

    execution_mode: str = os.getenv("EXECUTION_MODE", "docker")
    allow_local_execution: bool = _bool_env("ALLOW_LOCAL_EXECUTION", False)
    sandbox_image: str = os.getenv("SANDBOX_IMAGE", "agent-company-sandbox:py312")
    sandbox_memory: str = os.getenv("SANDBOX_MEMORY", "1g")
    sandbox_cpus: str = os.getenv("SANDBOX_CPUS", "1.0")
    sandbox_pids: int = int(os.getenv("SANDBOX_PIDS", "256"))
    sandbox_network: str = os.getenv("SANDBOX_NETWORK", "none")
    sandbox_user: str = os.getenv("SANDBOX_USER", "1000:1000")

    llm_mode: str = os.getenv("LLM_MODE", "mock")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")


settings = Settings()
