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

def test_cleanup_tolerates_locked_file(monkeypatch, tmp_path):
    monkeypatch.setattr("app.workers.workspace.settings.workspace_root", str(tmp_path))
    ws = RepositoryWorkspace("owner", "repo", "cleanup")
    ws.path.mkdir(parents=True)
    (ws.path / "locked.txt").write_text("x")
    real_rmtree = __import__("shutil").rmtree
    calls = {"n": 0}
    def flaky(path, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise PermissionError("locked")
        return real_rmtree(path, *args, **kwargs)
    monkeypatch.setattr("app.workers.workspace.shutil.rmtree", flaky)
    ws.cleanup()
    assert not ws.path.exists()


def test_context_selection_prioritizes_endpoint_entrypoint(tmp_path):
    from app.agents.coding import CodingAgent

    (tmp_path / "app").mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "app" / "main.py").write_text('from fastapi import FastAPI\napp = FastAPI()\n@app.get("/health")\ndef health(): return {"ok": True}\n')
    (tmp_path / "app" / "unrelated.py").write_text("VALUE = 1\n" * 1000)
    (tmp_path / "tests" / "test_api.py").write_text('def test_health(client):\n    assert client.get("/health").status_code == 200\n')
    context = CodingAgent._collect_context(tmp_path, "Add GET /version endpoint returning HTTP 200", [])
    assert list(context) == ["app/main.py", "tests/test_api.py"]
    assert len(context) <= 3
    assert sum(len(v) for v in context.values()) <= 14_000


def test_remote_url_never_contains_token(monkeypatch, tmp_path):
    monkeypatch.setattr("app.workers.workspace.settings.workspace_root", str(tmp_path))
    ws = RepositoryWorkspace("owner", "repo", "token", token="super-secret")
    assert ws._remote_url() == "https://github.com/owner/repo.git"
    assert "super-secret" not in ws._remote_url()


def test_reset_changes_discards_tracked_and_untracked(monkeypatch, tmp_path):
    monkeypatch.setattr("app.workers.workspace.settings.workspace_root", str(tmp_path))
    ws = RepositoryWorkspace("owner", "repo", "reset")
    ws.path.mkdir(parents=True)
    import subprocess
    subprocess.run(["git", "init"], cwd=ws.path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=ws.path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=ws.path, check=True)
    (ws.path / "a.txt").write_text("base")
    subprocess.run(["git", "add", "."], cwd=ws.path, check=True); subprocess.run(["git", "commit", "-m", "base"], cwd=ws.path, check=True, capture_output=True)
    (ws.path / "a.txt").write_text("changed"); (ws.path / "new.txt").write_text("new")
    ws.reset_changes()
    assert (ws.path / "a.txt").read_text() == "base"
    assert not (ws.path / "new.txt").exists()
