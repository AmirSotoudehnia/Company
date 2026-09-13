import json
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse

APP_VERSION = "0.5.0"

from app.agents.coding import CodingAgent
from app.core.settings import settings
from app.db import db, init_db
from app.integrations.github import get_issue
from app.integrations.webhooks import WebhookError, process_github_webhook, verify_signature
from app.models import ApprovalDecision, AutonomousCodeRequest, CodeJobRequest, GitHubImport, InstallationRegister, ProjectCreate, RepositoryRegister, TenantBootstrap, OpportunityCreate, SalesApprovalDecision, CustomerIntake, ChangeRequestCreate, OpsCheckCreate, InvoiceCreate
from app.orchestrator import Orchestrator
from app.sales_pipeline import SalesPipeline
from app.customer_ops import CustomerOps
from app.communication_pipeline import CommunicationPipeline
from app.operations import OperationsMonitor
from app.control_panel import control_job, dashboard_snapshot, set_agent_paused
from app.platform.audit import audit, list_audit
from app.platform.policy import RepositoryPolicy
from app.platform.queue import enqueue_job, list_jobs
from app.platform.tenancy import TenantError, create_tenant, register_installation, register_repository
from app.security.tenant_auth import require_tenant
from app.security.operator_auth import require_operator
from app.billing import create_invoice, list_invoices

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="Agent Company", version=APP_VERSION, lifespan=lifespan)
orch = Orchestrator()
sales = SalesPipeline()
customer_ops = CustomerOps()
communications = CommunicationPipeline()
operations = OperationsMonitor()


@app.get("/version")
def version():
    return {"version": APP_VERSION}


@app.get("/health")
def health():
    return {"ok": True, "version": APP_VERSION}


@app.post("/tenants/bootstrap")
def bootstrap_tenant(body: TenantBootstrap, x_bootstrap_token: str = Header(default="", alias="X-Bootstrap-Token")):
    if settings.bootstrap_token and x_bootstrap_token != settings.bootstrap_token:
        raise HTTPException(403, "Invalid bootstrap token")
    if not settings.bootstrap_token:
        with db() as conn:
            if conn.execute("SELECT COUNT(*) FROM tenants").fetchone()[0] > 0:
                raise HTTPException(403, "BOOTSTRAP_TOKEN must be configured before creating additional tenants")
    try:
        tenant, api_key = create_tenant(body.name, body.slug)
        audit(tenant["id"], "bootstrap", "tenant.created", f"tenant:{tenant['id']}")
        return {"tenant": tenant, "api_key": api_key, "warning": "This API key is shown only once."}
    except Exception as exc:
        raise HTTPException(400, str(exc))


@app.get("/tenant")
def tenant_info(tenant=Depends(require_tenant)):
    return tenant


@app.post("/tenant/installations")
def add_installation(body: InstallationRegister, tenant=Depends(require_tenant)):
    try:
        item = register_installation(tenant["id"], body.installation_id, body.account_login, body.account_type)
        audit(tenant["id"], "tenant-api", "installation.registered", f"installation:{body.installation_id}")
        return item
    except TenantError as exc:
        raise HTTPException(409, str(exc))


@app.post("/tenant/repositories")
def add_repository(body: RepositoryRegister, tenant=Depends(require_tenant)):
    policy = RepositoryPolicy(body.auto_code_enabled, body.max_attempts, body.test_command, body.required_label)
    try:
        item = register_repository(tenant["id"], body.installation_id, body.owner, body.name, body.default_branch, policy.to_json())
        audit(tenant["id"], "tenant-api", "repository.registered", f"repository:{item['id']}", item["id"], {"full_name": item["full_name"]})
        return item
    except TenantError as exc:
        raise HTTPException(409, str(exc))


@app.get("/tenant/repositories")
def tenant_repositories(tenant=Depends(require_tenant)):
    with db() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM repositories WHERE tenant_id=? ORDER BY id", (tenant["id"],))]


@app.post("/tenant/repositories/{repository_id}/jobs/code")
def queue_code_job(repository_id: int, body: CodeJobRequest, tenant=Depends(require_tenant)):
    with db() as conn:
        repo = conn.execute("SELECT * FROM repositories WHERE id=? AND tenant_id=? AND enabled=1", (repository_id, tenant["id"])).fetchone()
    if not repo:
        raise HTTPException(404, "Repository not found")
    policy = RepositoryPolicy.from_json(repo["policy_json"])
    if not policy.auto_code_enabled:
        raise HTTPException(409, "Autonomous coding is disabled for this repository")
    job = enqueue_job(tenant["id"], repository_id, "code_issue", {"issue_number": body.issue_number}, policy.max_attempts)
    audit(tenant["id"], "tenant-api", "job.enqueued", f"job:{job['id']}", repository_id, {"issue_number": body.issue_number})
    return job


@app.get("/tenant/jobs")
def tenant_jobs(limit: int = 100, tenant=Depends(require_tenant)):
    return list_jobs(tenant["id"], limit)


@app.get("/tenant/audit")
def tenant_audit(limit: int = 100, tenant=Depends(require_tenant)):
    return list_audit(tenant["id"], limit)


@app.post("/webhooks/github")
async def github_webhook(request: Request, x_hub_signature_256: str = Header(default="", alias="X-Hub-Signature-256"), x_github_delivery: str = Header(default="", alias="X-GitHub-Delivery"), x_github_event: str = Header(default="", alias="X-GitHub-Event")):
    body = await request.body()
    try:
        verify_signature(body, x_hub_signature_256)
        return process_github_webhook(x_github_delivery, x_github_event, body)
    except (WebhookError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(400, str(exc))


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
        result = agent.run_autonomous(task_id=f"issue-{body.issue_number}", branch=branch, title=f"Fix #{body.issue_number}: {title}", description=f"Autonomous implementation for GitHub issue #{body.issue_number}.\n\nCloses #{body.issue_number} after human review.", task=task, max_attempts=body.max_attempts)
        return result.__dict__
    except Exception as e:
        raise HTTPException(400, str(e))



@app.post("/opportunities")
def create_opportunity(body: OpportunityCreate):
    return sales.create(body.title, body.brief, body.source, body.source_url, body.budget)


@app.get("/opportunities")
def list_opportunities():
    return sales.list()


@app.get("/opportunities/{opportunity_id}")
def get_opportunity(opportunity_id: int):
    try:
        return sales.get(opportunity_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/opportunities/{opportunity_id}/approve/{approval_id}")
def approve_sales(opportunity_id: int, approval_id: int, body: SalesApprovalDecision):
    try:
        return sales.decide(opportunity_id, approval_id, body.approved, body.note)
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/engagements")
def create_engagement(body: CustomerIntake):
    try:
        milestones = [m.model_dump() for m in body.milestones]
        return customer_ops.onboard(body.opportunity_id, body.customer_name, body.email, body.company, body.scope, body.acceptance_criteria, milestones, body.budget, body.deadline)
    except ValueError as exc:
        raise HTTPException(409, str(exc))


@app.get("/engagements/{engagement_id}")
def get_engagement(engagement_id: int):
    try: return customer_ops.get(engagement_id)
    except ValueError as exc: raise HTTPException(404, str(exc))


@app.post("/engagements/{engagement_id}/scope-approval/{approval_id}")
def approve_scope(engagement_id: int, approval_id: int, body: ApprovalDecision):
    try: return customer_ops.approve_scope(engagement_id, approval_id, body.approved, body.note)
    except ValueError as exc: raise HTTPException(404, str(exc))


@app.post("/engagements/{engagement_id}/changes")
def create_change_request(engagement_id: int, body: ChangeRequestCreate):
    try: return customer_ops.request_change(engagement_id, body.description, body.budget_delta, body.deadline_delta_days)
    except ValueError as exc: raise HTTPException(404, str(exc))


@app.post("/engagements/{engagement_id}/communications/status")
def draft_customer_status(engagement_id: int):
    try: return communications.draft_status(engagement_id)
    except ValueError as exc: raise HTTPException(404, str(exc))


@app.get("/engagements/{engagement_id}/communications")
def list_customer_communications(engagement_id: int):
    return communications.list(engagement_id)


@app.post("/operations/checks")
def record_operations_check(body: OpsCheckCreate):
    return operations.record_check(body.name, body.target, body.healthy, body.detail)


@app.get("/operations/dashboard")
def operations_dashboard():
    return operations.dashboard()



@app.get("/control")
def control_panel_page(_=Depends(require_operator)):
    return FileResponse("app/static/control.html")


@app.get("/control/snapshot")
def control_snapshot(_=Depends(require_operator)):
    return dashboard_snapshot()


@app.post("/control/agents/{agent}/{action}")
def control_agent(agent: str, action: str, _=Depends(require_operator)):
    if action not in ("pause", "resume"):
        raise HTTPException(400, "Action must be pause or resume")
    try:
        return set_agent_paused(agent, action == "pause")
    except ValueError as exc:
        raise HTTPException(404, str(exc))


@app.post("/control/jobs/{job_id}/{action}")
def control_queued_job(job_id: int, action: str, _=Depends(require_operator)):
    try:
        return control_job(job_id, action)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.post("/billing/invoices")
def billing_create_invoice(body: InvoiceCreate, _=Depends(require_operator)):
    try: return create_invoice(body.engagement_id, body.amount, body.currency, body.due_date, body.note)
    except ValueError as exc: raise HTTPException(404, str(exc))

@app.get("/billing/invoices")
def billing_list_invoices(engagement_id: int | None = None, _=Depends(require_operator)):
    return list_invoices(engagement_id)
