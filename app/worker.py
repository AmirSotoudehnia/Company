from __future__ import annotations

import json
import os
import socket
import time

from app.agents.coding import CodingAgent
from app.db import db, init_db
from app.control_panel import is_agent_paused, set_agent_activity
from app.integrations.github import get_issue
from app.integrations.github_app import provider as github_app_provider
from app.platform.audit import audit
from app.platform.policy import RepositoryPolicy
from app.platform.queue import claim_next_job, complete_job, fail_job


def _worker_id() -> str:
    return os.getenv("WORKER_ID") or f"{socket.gethostname()}-{os.getpid()}"


def process_job(job: dict) -> dict:
    if job["kind"] != "code_issue":
        raise ValueError(f"Unsupported job kind: {job['kind']}")
    payload = json.loads(job["payload_json"])
    with db() as conn:
        repo_row = conn.execute("SELECT * FROM repositories WHERE id=? AND tenant_id=? AND enabled=1", (job["repository_id"], job["tenant_id"])).fetchone()
        if not repo_row:
            raise ValueError("Repository no longer available")
        repo = dict(repo_row)
    policy = RepositoryPolicy.from_json(repo["policy_json"])
    if not policy.auto_code_enabled:
        raise ValueError("Autonomous coding disabled by repository policy")

    installation_id = int(repo["installation_id"])
    token = github_app_provider.installation_token(installation_id)
    issue_number = int(payload["issue_number"])
    issue = get_issue(issue_number, owner=repo["owner"], repo=repo["name"], installation_id=installation_id, token=token)
    title = issue["title"]
    task = (issue.get("body") or title).strip()
    branch = f"agent/job-{job['id']}-issue-{issue_number}"

    if is_agent_paused("coding"):
        raise RuntimeError("Coding agent is paused")
    set_agent_activity("coding", "running", f"Coding GitHub issue #{issue_number}", job_id=job["id"])
    audit(job["tenant_id"], _worker_id(), "job.started", f"job:{job['id']}", repo["id"], {"issue_number": issue_number})
    agent = CodingAgent(repo["owner"], repo["name"], token=token, installation_id=installation_id)
    result = agent.run_autonomous(
        task_id=f"job-{job['id']}",
        branch=branch,
        title=f"Fix #{issue_number}: {title}",
        description=f"Autonomous implementation for GitHub issue #{issue_number}.\n\nHuman review is required before merge.",
        task=task,
        max_attempts=policy.max_attempts,
        test_command=policy.test_command,
        base_branch=repo["default_branch"],
    )
    result_dict = result.__dict__
    if not result.tests_passed:
        raise RuntimeError(result.test_output or "Tests failed")
    audit(job["tenant_id"], _worker_id(), "job.completed", f"job:{job['id']}", repo["id"], {"pull_request_url": result.pull_request_url, "attempts": result.attempts})
    set_agent_activity("coding", "completed", f"Completed job #{job['id']}", job_id=job["id"])
    return result_dict


def run_forever(poll_seconds: float = 2.0) -> None:
    init_db()
    worker = _worker_id()
    while True:
        job = claim_next_job(worker)
        if not job:
            time.sleep(poll_seconds)
            continue
        try:
            complete_job(job["id"], process_job(job))
        except Exception as exc:
            audit(job["tenant_id"], worker, "job.failed", f"job:{job['id']}", job["repository_id"], {"error": str(exc)[:2000]})
            fail_job(job["id"], str(exc))


if __name__ == "__main__":
    run_forever()
