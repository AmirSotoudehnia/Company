from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agents.patch_agent import PatchAgent
from app.core.settings import settings
from app.integrations.github import create_pull_request
from app.workers.sandbox import run_test_command
from app.workers.workspace import RepositoryWorkspace, WorkspaceError


@dataclass
class CodingRunResult:
    branch: str
    commit_sha: str
    tests_passed: bool
    test_output: str
    pull_request_url: str | None = None
    changed_files: list[str] | None = None
    attempts: int = 0


class CodingAgent:
    """Model proposes bounded edits; git and test execution stay outside the model."""

    def __init__(self, owner: str, repo: str, patch_agent: PatchAgent | None = None, token: str | None = None, installation_id: int | None = None):
        self.owner = owner
        self.repo = repo
        self.patch_agent = patch_agent or PatchAgent()
        self.token = token
        self.installation_id = installation_id

    def run_autonomous(self, task_id: str, branch: str, title: str, description: str, task: str, max_attempts: int = 3, test_command: str | None = None, base_branch: str = "main") -> CodingRunResult:
        ws = RepositoryWorkspace(self.owner, self.repo, task_id, token=self.token)
        test_command = test_command or settings.test_command
        try:
            ws.prepare(base_branch=base_branch)
            branch_result = ws.create_branch(branch)
            if not branch_result.ok:
                raise WorkspaceError(branch_result.stderr or branch_result.stdout)
            feedback = ""
            changed_files: list[str] = []
            latest_output = ""
            for attempt in range(1, max_attempts + 1):
                context = self._collect_context(ws.path, task, changed_files)
                plan = self.patch_agent.propose(task=task, context=context, test_feedback=feedback)
                changed_files = self.patch_agent.apply(ws.path, plan)
                test = run_test_command(ws.path, test_command)
                latest_output = (test.stdout + "\n" + test.stderr).strip()
                if test.ok:
                    sha = ws.commit_and_push(branch, f"agent: {title}")
                    pr = create_pull_request(
                        title,
                        description + f"\n\nAgent attempts: {attempt}\nChanged files: " + ", ".join(changed_files),
                        branch,
                        base=base_branch,
                        owner=self.owner,
                        repo=self.repo,
                        installation_id=self.installation_id,
                        token=self.token,
                    )
                    return CodingRunResult(branch, sha, True, latest_output, pr.get("html_url"), changed_files, attempt)
                feedback = latest_output
            return CodingRunResult(branch, "", False, latest_output, changed_files=changed_files, attempts=max_attempts)
        finally:
            ws.cleanup()

    def run(self, task_id: str, branch: str, apply_change, title: str, description: str) -> CodingRunResult:
        ws = RepositoryWorkspace(self.owner, self.repo, task_id, token=self.token)
        try:
            ws.prepare()
            branch_result = ws.create_branch(branch)
            if not branch_result.ok:
                raise WorkspaceError(branch_result.stderr or branch_result.stdout)
            apply_change(ws.path)
            test = run_test_command(ws.path, settings.test_command)
            output = (test.stdout + "\n" + test.stderr).strip()
            if not test.ok:
                return CodingRunResult(branch, "", False, output)
            changed = ws.changed_files()
            sha = ws.commit_and_push(branch, f"agent: {title}")
            pr = create_pull_request(title, description, branch, owner=self.owner, repo=self.repo, installation_id=self.installation_id, token=self.token)
            return CodingRunResult(branch, sha, True, output, pr.get("html_url"), changed, 1)
        finally:
            ws.cleanup()

    @staticmethod
    def _collect_context(root: Path, task: str, preferred: list[str]) -> dict[str, str]:
        blocked_dirs = {".git", ".venv", "node_modules", "build", "dist", ".dart_tool"}
        allowed_suffixes = {".py", ".md", ".toml", ".txt", ".json", ".yaml", ".yml", ".js", ".ts", ".tsx", ".jsx", ".dart", ".kt", ".kts", ".java", ".swift", ".html", ".css"}
        candidates: list[Path] = []
        for path in root.rglob("*"):
            if not path.is_file() or any(part in blocked_dirs for part in path.parts):
                continue
            if path.suffix.lower() in allowed_suffixes or path.name in {"Dockerfile", "Makefile"}:
                candidates.append(path)
        preferred_set = set(preferred)
        task_terms = {w.lower() for w in task.replace("/", " ").replace("_", " ").split() if len(w) > 3}
        def score(path: Path) -> tuple[int, int, str]:
            rel = path.relative_to(root).as_posix()
            s = 100 if rel in preferred_set else 0
            s += sum(5 for term in task_terms if term in rel.lower())
            if rel.startswith("tests/"):
                s += 3
            return (-s, len(rel), rel)
        result: dict[str, str] = {}
        total = 0
        for path in sorted(candidates, key=score):
            if len(result) >= 24 or total >= 120_000:
                break
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if len(content) > 20_000:
                content = content[:20_000] + "\n# ... truncated ..."
            rel = path.relative_to(root).as_posix()
            result[rel] = content
            total += len(content)
        return result
