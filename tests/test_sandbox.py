from pathlib import Path

import pytest

from app.core.settings import settings
from app.workers import sandbox as sandbox_module
from app.workers.sandbox import DockerSandbox, run_test_command
from app.workers.workspace import WorkspaceError


def test_local_execution_is_denied_by_default(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "execution_mode", "local")
    monkeypatch.setattr(settings, "allow_local_execution", False)
    with pytest.raises(WorkspaceError):
        run_test_command(tmp_path, "python -m pytest -q")


def test_docker_sandbox_uses_hardening_flags(tmp_path, monkeypatch):
    workspace = Path(tmp_path)
    calls = []

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return Result()

    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)
    runner = DockerSandbox(image="sandbox:test")
    result = runner.run(workspace, "python -m pytest -q")

    assert result.ok
    docker_command = calls[-1][0]
    assert "--network" in docker_command
    assert "none" in docker_command
    assert ["--cap-drop", "ALL"] == docker_command[docker_command.index("--cap-drop"):docker_command.index("--cap-drop") + 2]
    assert "no-new-privileges:true" in docker_command
    assert "--read-only" in docker_command
    assert "sandbox:test" in docker_command


def test_docker_sandbox_does_not_forward_host_environment(tmp_path, monkeypatch):
    seen = []

    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        seen.append((command, kwargs))
        return Result()

    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)
    DockerSandbox(image="sandbox:test").run(Path(tmp_path), "python -m pytest -q")
    command = seen[-1][0]
    rendered = " ".join(command)
    assert "GITHUB_TOKEN" not in rendered
    assert "LLM_API_KEY" not in rendered


def test_docker_mount_uses_windows_safe_key_value_syntax(tmp_path, monkeypatch):
    calls = []
    class Result:
        returncode = 0
        stdout = "ok"
        stderr = ""
    def fake_run(command, **kwargs):
        calls.append(command)
        return Result()
    monkeypatch.setattr(sandbox_module.subprocess, "run", fake_run)
    DockerSandbox(image="sandbox:test").run(Path(tmp_path), "python -m pytest -q")
    command = calls[-1]
    mount = command[command.index("--mount") + 1]
    assert "source=" in mount and "target=/workspace" in mount
    assert not mount.endswith(",rw")
