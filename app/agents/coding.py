from __future__ import annotations

from dataclasses import dataclass

from app.core.settings import settings
from app.integrations.github import create_pull_request
from app.workers.workspace import RepositoryWorkspace, WorkspaceError


@dataclass
class CodingRunResult:
    branch: str
    commit_sha: str
    tests_passed: bool
    test_output: str
    pull_request_url: str | None = None


class CodingAgent:
    """Executes an already-prepared code change in a disposable workspace.

    The next stage will plug a model-backed patch generator into `apply_change`.
    Keeping execution and generation separate makes permissions and auditing
    much safer than giving a model unrestricted shell access.
    """

    def __init__(self, owner: str, repo: str):
        self.owner = owner
        self.repo = repo

    def run(self, task_id: str, branch: str, apply_change, title: str, description: str) -> CodingRunResult:
        ws = RepositoryWorkspace(self.owner, self.repo, task_id)
        try:
            ws.prepare()
            branch_result = ws.create_branch(branch)
            if not branch_result.ok:
                raise WorkspaceError(branch_result.stderr or branch_result.stdout)

            apply_change(ws.path)

            test = ws.run_shell_command(settings.test_command)
            if not test.ok:
                return CodingRunResult(
                    branch=branch,
                    commit_sha="",
                    tests_passed=False,
                    test_output=(test.stdout + "\n" + test.stderr).strip(),
                )

            sha = ws.commit_and_push(branch, f"agent: {title}")
            pr = create_pull_request(title, description, branch)
            return CodingRunResult(
                branch=branch,
                commit_sha=sha,
                tests_passed=True,
                test_output=(test.stdout + "\n" + test.stderr).strip(),
                pull_request_url=pr.get("html_url"),
            )
        finally:
            ws.cleanup()
