from fastapi import FastAPI, HTTPException

from app.agents.coding import CodingAgent
from app.core.settings import settings
from app.db import init_db, db
from app.integrations.github import get_issue
from app.models import ApprovalDecision, AutonomousCodeRequest, GitHubImport, ProjectCreate
from app.orchestrator import Orchestrator

app = FastAPI(title="Agent Company", version="0.3.0")
orch = Orchestrator()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/projects")
def create_project(body: ProjectCreate):
    with db() as conn:
        cur = conn.execute("INSERT INTO projects(name,brief,risk_level) VALUES(?,?,?)", (body.name, body.brief, body.risk_level))
        project_id = cur.lastrowid
    return orch.snapshot(project_id)


@app.get("/projects")
def list_projects():
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM projects ORDER BY id DESC")]


@app.get("/projects/{project_id}")
def get_project(project_id: int):
    try:
        return orch.snapshot(project_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/projects/{project_id}/run")
def run_project(project_id: int):
    try:
        return orch.run(project_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post("/projects/{project_id}/approve/{approval_id}")
def decide_approval(project_id: int, approval_id: int, body: ApprovalDecision):
    with db() as conn:
        ap = conn.execute("SELECT * FROM approvals WHERE id=? AND project_id=?", (approval_id, project_id)).fetchone()
        if not ap:
            raise HTTPException(404, "Approval not found")
        status = "approved" if body.approved else "rejected"
        conn.execute("UPDATE approvals SET status=?, note=? WHERE id=?", (status, body.note, approval_id))
        if body.approved and ap["kind"] == "production_delivery":
            conn.execute("UPDATE projects SET status='delivered' WHERE id=?", (project_id,))
    return orch.snapshot(project_id)


@app.post("/github/import")
def import_github_issue(body: GitHubImport):
    try:
        issue = get_issue(body.issue_number)
    except Exception as e:
        raise HTTPException(400, str(e))
    return create_project(ProjectCreate(name=f"GitHub #{body.issue_number}: {issue['title']}", brief=issue.get("body") or issue["title"]))


@app.post("/github/code")
def autonomously_code_issue(body: AutonomousCodeRequest):
    if not settings.github_owner or not settings.github_repo:
        raise HTTPException(400, "GITHUB_OWNER and GITHUB_REPO must be configured")
    try:
        issue = get_issue(body.issue_number)
        title = issue["title"]
        task = (issue.get("body") or title).strip()
        branch = body.branch or f"agent/issue-{body.issue_number}"
        agent = CodingAgent(settings.github_owner, settings.github_repo)
        result = agent.run_autonomous(
            task_id=f"issue-{body.issue_number}",
            branch=branch,
            title=f"Fix #{body.issue_number}: {title}",
            description=f"Autonomous implementation for GitHub issue #{body.issue_number}.\n\nCloses #{body.issue_number} after human review.",
            task=task,
            max_attempts=body.max_attempts,
        )
        return result.__dict__
    except Exception as e:
        raise HTTPException(400, str(e))
