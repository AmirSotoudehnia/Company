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
    target = tmp_path / "app" / "example.py"
    target.parent.mkdir()
    target.write_text("VALUE = 1\n", encoding="utf-8")
    agent = PatchAgent(client=FakeLLM({
        "summary": "update app",
        "edits": [{"path": "app/example.py", "find": "VALUE = 1", "replace": "VALUE = 2"}],
    }))
    plan = agent.propose("change value", {"app/example.py": "VALUE = 1\n"})
    changed = agent.apply(tmp_path, plan)
    assert changed == ["app/example.py"]
    assert target.read_text() == "VALUE = 2\n"


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

def test_patch_agent_accepts_fenced_wrapped_plan(tmp_path: Path):
    payload = {"patch": {"summary": "ok", "edits": [{"path": "app/x.py", "content": "X = 1\n"}]}}
    class FencedLLM:
        def complete(self, system_prompt, user_prompt):
            return "```json\n" + json.dumps(payload) + "\n```"
    agent = PatchAgent(client=FencedLLM())
    plan = agent.propose("task", {})
    assert agent.apply(tmp_path, plan) == ["app/x.py"]

def test_patch_agent_accepts_arbitrary_single_wrapper():
    payload = {"output": {"data": {"summary": "ok", "edits": [{"path": "x.py", "content": "x=1\n"}]}}}
    agent = PatchAgent(client=FakeLLM(payload))
    plan = agent.propose("task", {})
    assert plan.edits[0].path == "x.py"


def test_local_llm_memory_settings_have_safe_defaults():
    from app.core.settings import Settings
    cfg = Settings()
    assert cfg.llm_num_ctx >= 1024
    assert cfg.llm_num_predict > 0
    assert cfg.llm_keep_alive is not None


def test_patch_agent_rejects_ambiguous_find(tmp_path: Path):
    target = tmp_path / "x.py"
    target.write_text("A = 1\nA = 1\n", encoding="utf-8")
    agent = PatchAgent(client=FakeLLM({"summary":"x","edits":[{"path":"x.py","find":"A = 1","replace":"A = 2"}]}))
    plan = agent.propose("task", {"x.py": target.read_text()})
    with pytest.raises(PatchPlanError):
        agent.apply(tmp_path, plan)

def test_patch_agent_allows_content_only_for_new_file(tmp_path: Path):
    agent = PatchAgent(client=FakeLLM({"summary":"new","edits":[{"path":"new.py","content":"X = 1\n"}]}))
    plan = agent.propose("task", {})
    agent.apply(tmp_path, plan)
    assert (tmp_path / "new.py").read_text() == "X = 1\n"


def test_prompt_requires_acceptance_feedback_correction():
    from app.agents.patch_agent import SYSTEM_PROMPT
    assert "mandatory correction" in SYSTEM_PROMPT
    assert "every explicit acceptance criterion" in SYSTEM_PROMPT

def test_patch_agent_inserts_after_unique_anchor(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("A = 1\nB = 2\n", encoding="utf-8")
    agent = PatchAgent(client=FakeLLM({"summary":"insert","edits":[{"path":"app.py","anchor":"A = 1\n","insert_after":"VERSION = 3\n"}]}))
    plan = agent.propose("insert version", {"app.py": target.read_text()})
    assert agent.apply(tmp_path, plan) == ["app.py"]
    assert target.read_text() == "A = 1\nVERSION = 3\nB = 2\n"


def test_patch_agent_rejects_ambiguous_anchor(tmp_path: Path):
    target = tmp_path / "app.py"
    target.write_text("A = 1\nA = 1\n", encoding="utf-8")
    agent = PatchAgent(client=FakeLLM({"summary":"insert","edits":[{"path":"app.py","anchor":"A = 1","insert_after":"\nB = 2"}]}))
    plan = agent.propose("insert", {"app.py": target.read_text()})
    with pytest.raises(PatchPlanError):
        agent.apply(tmp_path, plan)


def test_patch_agent_extracts_json_from_model_prose(tmp_path: Path):
    class NoisyLLM:
        def complete(self, system_prompt, user_prompt):
            payload = {"summary": "ok", "edits": [{"path": "x.py", "content": "X = 1\n"}]}
            return "Here is the patch:\n" + json.dumps(payload) + "\nDone."
    agent = PatchAgent(client=NoisyLLM())
    plan = agent.propose("task", {})
    assert agent.apply(tmp_path, plan) == ["x.py"]
    assert (tmp_path / "x.py").read_text() == "X = 1\n"


def test_patch_agent_does_not_guess_truncated_json():
    class BrokenLLM:
        def complete(self, system_prompt, user_prompt):
            return '{"summary":"bad","edits":[{"path":"x.py","content":"X=1"}'
    with pytest.raises(PatchPlanError):
        PatchAgent(client=BrokenLLM()).propose("task", {})
