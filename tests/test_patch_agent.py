import json
from pathlib import Path

import pytest

from app.agents.patch_agent import PatchAgent, PatchPlanError


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        return json.dumps(self.payload)


def test_patch_agent_applies_safe_edit(tmp_path: Path):
    agent = PatchAgent(client=FakeLLM({
        "summary": "update app",
        "edits": [{"path": "app/example.py", "content": "VALUE = 2\n"}],
    }))
    plan = agent.propose("change value", {"app/example.py": "VALUE = 1\n"})
    changed = agent.apply(tmp_path, plan)
    assert changed == ["app/example.py"]
    assert (tmp_path / "app/example.py").read_text() == "VALUE = 2\n"


def test_patch_agent_blocks_parent_escape(tmp_path: Path):
    agent = PatchAgent(client=FakeLLM({
        "summary": "bad",
        "edits": [{"path": "../secret.txt", "content": "nope"}],
    }))
    with pytest.raises(PatchPlanError):
        agent.propose("bad task", {})


def test_patch_agent_blocks_env_file(tmp_path: Path):
    agent = PatchAgent(client=FakeLLM({
        "summary": "bad",
        "edits": [{"path": ".env", "content": "TOKEN=x"}],
    }))
    with pytest.raises(PatchPlanError):
        agent.propose("bad task", {})


def test_patch_agent_enforces_file_limit():
    payload = {
        "summary": "too many",
        "edits": [{"path": f"f{i}.py", "content": "x=1\n"} for i in range(3)],
    }
    agent = PatchAgent(client=FakeLLM(payload), max_files=2)
    with pytest.raises(PatchPlanError):
        agent.propose("task", {})
