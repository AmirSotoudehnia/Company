from app.db import db
from app.agents.manager import ProjectManagerAgent
from app.agents.architect import ArchitectAgent
from app.agents.developer import DeveloperAgent
from app.agents.qa import QAAgent, BugFixAgent
from app.agents.delivery import DeliveryAgent


class Orchestrator:
    def _event(self, project_id, actor, event, detail=""):
        with db() as conn:
            conn.execute("INSERT INTO events(project_id,actor,event,detail) VALUES(?,?,?,?)", (project_id, actor, event, detail))

    def _project(self, project_id):
        with db() as conn:
            row = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            return dict(row) if row else None

    def _tasks(self, project_id):
        with db() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY id", (project_id,))]

    def _set_status(self, project_id, status):
        with db() as conn:
            conn.execute("UPDATE projects SET status=? WHERE id=?", (status, project_id))

    def _seed_tasks(self, project_id):
        with db() as conn:
            count = conn.execute("SELECT COUNT(*) c FROM tasks WHERE project_id=?", (project_id,)).fetchone()["c"]
            if count:
                return
            conn.executemany("INSERT INTO tasks(project_id,title,description,role) VALUES(?,?,?,?)", [
                (project_id, "Create implementation plan", "Define objective, acceptance criteria, workstreams, and risks", "project_manager"),
                (project_id, "Create architecture plan", "Inspect stack, entrypoints, tests, constraints, and implementation order", "architect"),
                (project_id, "Implement requested functionality", "Build requested change", "developer"),
                (project_id, "Run QA and regression checks", "Validate acceptance criteria", "qa"),
                (project_id, "Prepare release package", "Create delivery notes", "delivery"),
            ])

    def _run_agent(self, project_id, agent):
        result = agent.run(self._project(project_id), self._tasks(project_id))
        self._event(project_id, agent.name, "completed", result.summary)
        if result.next_status:
            self._set_status(project_id, result.next_status)
        return result

    def run(self, project_id):
        project = self._project(project_id)
        if not project:
            raise ValueError("Project not found")
        self._seed_tasks(project_id)
        status = project["status"]
        if status == "new":
            self._run_agent(project_id, ProjectManagerAgent()); status = "pm_planned"
        if status == "pm_planned":
            self._run_agent(project_id, ArchitectAgent()); status = "planned"
        if status == "planned":
            self._run_agent(project_id, DeveloperAgent()); status = "development_done"
        if status in ("development_done", "fixed"):
            result = self._run_agent(project_id, QAAgent())
            if result.next_status == "bug_found":
                self._run_agent(project_id, BugFixAgent())
                self._set_status(project_id, "qa_passed")
            status = self._project(project_id)["status"]
        if status == "qa_passed":
            self._run_agent(project_id, DeliveryAgent())
            with db() as conn:
                existing = conn.execute("SELECT id FROM approvals WHERE project_id=? AND kind='production_delivery'", (project_id,)).fetchone()
                if not existing:
                    conn.execute("INSERT INTO approvals(project_id,kind,status,note) VALUES(?,?,?,?)", (project_id, "production_delivery", "pending", "Approve final production delivery"))
        return self.snapshot(project_id)

    def snapshot(self, project_id):
        with db() as conn:
            project = conn.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
            if not project:
                raise ValueError("Project not found")
            tasks = [dict(r) for r in conn.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY id", (project_id,))]
            approvals = [dict(r) for r in conn.execute("SELECT * FROM approvals WHERE project_id=? ORDER BY id", (project_id,))]
            events = [dict(r) for r in conn.execute("SELECT * FROM events WHERE project_id=? ORDER BY id", (project_id,))]
        return {"project": dict(project), "tasks": tasks, "approvals": approvals, "events": events}
