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
