from pathlib import Path

from app.agents.acceptance import AcceptanceReviewer


def test_rejects_missing_version_route(tmp_path: Path):
    main = tmp_path / "app" / "main.py"
    main.parent.mkdir()
    main.write_text('app = FastAPI(version="0.5.0")\n', encoding="utf-8")
    result = AcceptanceReviewer().review(tmp_path, "Add GET /version endpoint")
    assert not result.ok
    assert "/version" in result.feedback


def test_accepts_version_route_with_constant(tmp_path: Path):
    main = tmp_path / "app" / "main.py"
    main.parent.mkdir()
    main.write_text('APP_VERSION = "0.5.0"\n@app.get("/version")\ndef version():\n    return {"version": APP_VERSION}\n', encoding="utf-8")
    result = AcceptanceReviewer().review(tmp_path, "Add GET /version endpoint")
    assert result.ok


def test_rejects_task_requiring_tests_when_no_test_file_changed(tmp_path: Path):
    main = tmp_path / "app" / "main.py"
    main.parent.mkdir()
    main.write_text('APP_VERSION = "1"\n@app.get("/version")\ndef version(): return {"version": APP_VERSION}\n', encoding="utf-8")
    result = AcceptanceReviewer().review(tmp_path, "Add /version endpoint and tests", ["app/main.py"])
    assert not result.ok
    assert "test file" in result.feedback


def test_requires_version_test_coverage(tmp_path: Path):
    main = tmp_path / "app" / "main.py"; main.parent.mkdir()
    main.write_text('APP_VERSION = "1"\n@app.get("/version")\ndef version(): return {"version": APP_VERSION}\n', encoding="utf-8")
    tests = tmp_path / "tests"; tests.mkdir(); (tests / "test_api.py").write_text('def test_health(): pass\n')
    result = AcceptanceReviewer().review(tmp_path, "Add /version endpoint and tests", ["app/main.py", "tests/test_api.py"])
    assert not result.ok
    assert "cover /version" in result.feedback
