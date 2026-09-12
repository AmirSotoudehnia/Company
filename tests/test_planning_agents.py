from pathlib import Path
from app.agents.manager import ProjectManagerAgent
from app.agents.architect import ArchitectAgent

def test_pm_builds_acceptance_and_workstreams():
    plan = ProjectManagerAgent().plan({"brief":"Add secure login endpoint", "risk_level":"high"})
    assert plan.objective == "Add secure login endpoint"
    assert any("tests" in item.lower() for item in plan.acceptance_criteria)
    assert "architecture" in plan.workstreams
    assert plan.risks

def test_architect_inspects_repository(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("fastapi\n")
    (tmp_path / "app").mkdir(); (tmp_path / "app" / "main.py").write_text("app = object()\n")
    (tmp_path / "tests").mkdir(); (tmp_path / "tests" / "test_api.py").write_text("def test_x(): pass\n")
    plan = ArchitectAgent().inspect(tmp_path)
    assert "python" in plan.stack
    assert "app/main.py" in plan.entrypoints
    assert "tests/test_api.py" in plan.test_locations
