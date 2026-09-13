import os
import tempfile

fd, path = tempfile.mkstemp(prefix="control_panel_", suffix=".db")
os.close(fd)
os.environ["AGENT_COMPANY_DB"] = path

from app.control_panel import dashboard_snapshot, is_agent_paused, set_agent_activity, set_agent_paused
from app.db import init_db


def test_agent_activity_is_visible_and_controllable():
    init_db()
    set_agent_activity("qa", "running", "Testing project", project_id=7)
    snapshot = dashboard_snapshot()
    qa = next(a for a in snapshot["agents"] if a["agent"] == "qa")
    assert qa["status"] == "running"
    assert qa["project_id"] == 7
    set_agent_paused("qa", True)
    assert is_agent_paused("qa") is True
    qa = next(a for a in dashboard_snapshot()["agents"] if a["agent"] == "qa")
    assert qa["status"] == "paused"
    set_agent_paused("qa", False)


def test_orchestrator_records_agent_activity():
    from app.orchestrator import Orchestrator
    from app.db import db
    init_db()
    with db() as conn:
        cur = conn.execute("INSERT INTO projects(name,brief) VALUES('Panel project','Build a normal API feature')")
        project_id = cur.lastrowid
    Orchestrator().run(project_id)
    snapshot = dashboard_snapshot()
    pm = next(a for a in snapshot["agents"] if a["agent"] == "project_manager")
    assert pm["status"] == "completed"
    assert pm["project_id"] == project_id
    assert any(a["status"] == "completed" for a in snapshot["agents"])
