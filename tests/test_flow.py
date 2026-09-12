import os
import tempfile

fd, path = tempfile.mkstemp(prefix="agent_company_", suffix=".db")
os.close(fd)
os.environ["AGENT_COMPANY_DB"] = path

from app.db import init_db, db
from app.orchestrator import Orchestrator


def test_end_to_end_flow():
    init_db()
    with db() as conn:
        cur = conn.execute("INSERT INTO projects(name,brief,risk_level) VALUES(?,?,?)", ("Demo", "Build a small landing page with contact form", "normal"))
        pid = cur.lastrowid
    snap = Orchestrator().run(pid)
    assert snap["project"]["status"] == "awaiting_delivery_approval"
    assert len(snap["approvals"]) == 1

def test_flow_runs_pm_before_architect():
    init_db()
    with db() as conn:
        cur = conn.execute("INSERT INTO projects(name,brief,risk_level) VALUES(?,?,?)", ("Planned", "Build API", "normal"))
        pid = cur.lastrowid
    snap = Orchestrator().run(pid)
    actors = [event["actor"] for event in snap["events"]]
    assert "project_manager" in actors
    assert "architect" in actors
    assert actors.index("project_manager") < actors.index("architect")
    assert any(task["role"] == "architect" for task in snap["tasks"])
