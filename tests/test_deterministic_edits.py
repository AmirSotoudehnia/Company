from pathlib import Path

from app.agents.deterministic_edits import DeterministicEditor


def _repo(tmp_path: Path) -> Path:
    app = tmp_path / "app"
    app.mkdir()
    (app / "main.py").write_text(
        'from fastapi import FastAPI\n\napp = FastAPI(title="X", version="0.5.0")\n\n'
        '@app.get("/health")\ndef health():\n    return {"ok": True, "version": app.version}\n',
        encoding="utf-8",
    )
    return tmp_path


def test_version_endpoint_is_applied_without_model_patch_mechanics(tmp_path: Path):
    root = _repo(tmp_path)
    changed = DeterministicEditor().apply(root, "Add GET /version endpoint")
    source = (root / "app" / "main.py").read_text(encoding="utf-8")
    assert changed == ["app/main.py"]
    assert 'APP_VERSION = "0.5.0"' in source
    assert 'version=APP_VERSION' in source
    assert '@app.get("/version")' in source
    assert 'return {"version": APP_VERSION}' in source


def test_version_endpoint_edit_is_idempotent(tmp_path: Path):
    root = _repo(tmp_path)
    editor = DeterministicEditor()
    editor.apply(root, "Add GET /version endpoint")
    editor.apply(root, "Add GET /version endpoint")
    source = (root / "app" / "main.py").read_text(encoding="utf-8")
    assert source.count('APP_VERSION = "0.5.0"') == 1
    assert source.count('@app.get("/version")') == 1


def test_unrecognized_task_is_left_for_model(tmp_path: Path):
    root = _repo(tmp_path)
    before = (root / "app" / "main.py").read_text(encoding="utf-8")
    assert DeterministicEditor().apply(root, "Refactor tenant authentication") == []
    assert (root / "app" / "main.py").read_text(encoding="utf-8") == before


def test_version_task_creates_endpoint_test_when_needed(tmp_path: Path):
    root = _repo(tmp_path)
    changed = DeterministicEditor().apply(root, "Add GET /version endpoint and automated tests")
    test_file = root / "tests" / "test_version_endpoint.py"
    assert "tests/test_version_endpoint.py" in changed
    assert test_file.is_file()
    content = test_file.read_text(encoding="utf-8")
    assert 'client.get("/version")' in content
    assert 'response.json() == {"version": APP_VERSION}' in content
