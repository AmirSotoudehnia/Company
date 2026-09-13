import os
from dataclasses import dataclass
from pathlib import Path


def _load_local_env() -> None:
    path = Path(os.getenv("AGENT_COMPANY_ENV_FILE", ".env.local"))
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()



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
    control_token: str = os.getenv("CONTROL_TOKEN", "")
    control_allow_local_unauth: bool = _bool_env("CONTROL_ALLOW_LOCAL_UNAUTH", True)
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
    llm_num_ctx: int = int(os.getenv("LLM_NUM_CTX", "2048"))
    llm_num_predict: int = int(os.getenv("LLM_NUM_PREDICT", "1536"))
    llm_keep_alive: str = os.getenv("LLM_KEEP_ALIVE", "0")


settings = Settings()
