from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class RepositoryPolicy:
    auto_code_enabled: bool = True
    max_attempts: int = 3
    test_command: str = "python -m pytest -q"
    required_label: str = "agent:run"

    @classmethod
    def from_json(cls, raw: str | None) -> "RepositoryPolicy":
        try:
            data = json.loads(raw or "{}")
        except json.JSONDecodeError:
            data = {}
        return cls(
            auto_code_enabled=bool(data.get("auto_code_enabled", True)),
            max_attempts=max(1, min(int(data.get("max_attempts", 3)), 5)),
            test_command=str(data.get("test_command") or "python -m pytest -q")[:300],
            required_label=str(data.get("required_label") or "agent:run")[:80],
        )

    def to_json(self) -> str:
        return json.dumps(self.__dict__, sort_keys=True)
