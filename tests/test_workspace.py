from pathlib import Path
from app.workers.workspace import RepositoryWorkspace


def test_task_id_is_sanitized(monkeypatch, tmp_path):
    monkeypatch.setattr("app.workers.workspace.settings.workspace_root", str(tmp_path))
    ws = RepositoryWorkspace("owner", "repo", "../../danger / task")
    assert ws.path.parent == Path(tmp_path)
    assert ".." not in ws.path.name


def test_shell_command_is_split_without_shell_expansion(monkeypatch, tmp_path):
    monkeypatch.setattr("app.workers.workspace.settings.workspace_root", str(tmp_path))
    ws = RepositoryWorkspace("owner", "repo", "1")
    ws.path.mkdir(parents=True)
    result = ws.run_shell_command("python -c 'print(123)'")
    assert result.ok
    assert "123" in result.stdout
