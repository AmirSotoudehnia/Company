from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agents.acceptance import AcceptanceReviewer
from app.agents.deterministic_edits import DeterministicEditor, DeterministicEditError
from app.agents.patch_agent import PatchAgent, PatchPlanError
from app.agents.repository_gates import quality_findings, security_findings
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
        self.acceptance_reviewer = AcceptanceReviewer()
        self.deterministic_editor = DeterministicEditor()
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
            try:
                deterministic = self.deterministic_editor.apply(ws.path, task)
                if deterministic:
                    changed_files = deterministic
                    test = run_test_command(ws.path, test_command)
                    latest_output = (test.stdout + "\n" + test.stderr).strip()
                    if test.ok:
                        acceptance = self.acceptance_reviewer.review(ws.path, task, changed_files)
                        if acceptance.ok:
                            gates = quality_findings(ws.path, changed_files) + security_findings(ws.path, changed_files)
                            if gates:
                                return CodingRunResult(branch, "", False, "Repository gates blocked changes: " + "; ".join(gates), changed_files=changed_files, attempts=0)
                            sha = ws.commit_and_push(branch, f"agent: {title}")
                            pr = create_pull_request(
                                title, description + "\n\nDeterministic implementation\nChanged files: " + ", ".join(changed_files),
                                branch, base=base_branch, owner=self.owner, repo=self.repo,
                                installation_id=self.installation_id, token=self.token,
                            )
                            return CodingRunResult(branch, sha, True, latest_output, pr.get("html_url"), changed_files, 0)
                        feedback = acceptance.feedback
                    else:
                        feedback = latest_output
            except DeterministicEditError as exc:
                feedback = f"Deterministic edit unavailable: {exc}"
            for attempt in range(1, max_attempts + 1):
                ws.reset_changes()
                changed_files = []
                context = self._collect_context(ws.path, task, changed_files)
                try:
                    plan = self.patch_agent.propose(task=task, context=context, test_feedback=feedback)
                    changed_files = self.patch_agent.apply(ws.path, plan)
                except PatchPlanError as exc:
                    feedback = f"Patch rejected: {exc}. Re-read the CURRENT file content provided on the next attempt and use an exact find string from it."
                    latest_output = feedback
                    continue
                test = run_test_command(ws.path, test_command)
                latest_output = (test.stdout + "\n" + test.stderr).strip()
                if test.ok:
                    acceptance = self.acceptance_reviewer.review(ws.path, task, changed_files)
                    if not acceptance.ok:
                        feedback = acceptance.feedback
                        latest_output = feedback
                        continue
                    gates = quality_findings(ws.path, changed_files) + security_findings(ws.path, changed_files)
                    if gates:
                        feedback = "Repository gates blocked changes: " + "; ".join(gates)
                        latest_output = feedback
                        continue
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
        blocked_dirs = {".git", ".venv", "node_modules", "build", "dist", ".dart_tool", "workspaces", "ollama-models"}
        allowed_suffixes = {".py", ".md", ".toml", ".txt", ".json", ".yaml", ".yml", ".js", ".ts", ".tsx", ".jsx", ".dart", ".kt", ".kts", ".java", ".swift", ".html", ".css"}
        stop_words = {"add", "with", "from", "that", "this", "must", "should", "current", "application", "automated", "existing", "continue", "pass", "issue", "intended", "first", "validation", "after", "human", "review"}
        task_terms = {w.strip(".,:;()[]{}'\"").lower() for w in task.replace("/", " ").replace("_", " ").replace("-", " ").split()}
        task_terms = {w for w in task_terms if len(w) >= 4 and w not in stop_words}
        preferred_set = set(preferred)
        candidates: list[tuple[Path, str, int]] = []
        endpoint_task = any(word in task.lower() for word in ("endpoint", "route", "api", "http"))
        if endpoint_task:
            result: dict[str, str] = {}
            for rel in ("app/main.py", "main.py", "src/main.py"):
                entry = root / rel
                if entry.is_file():
                    try:
                        result[rel] = entry.read_text(encoding="utf-8")[:3_500]
                    except (UnicodeDecodeError, OSError):
                        pass
                    break
            test_candidates = sorted((root / "tests").glob("test_*.py")) if (root / "tests").is_dir() else []
            for test_file in test_candidates:
                try:
                    content = test_file.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                lower = content.lower()
                if any(key in lower for key in ("testclient", "client", "/health", "fastapi")):
                    result[test_file.relative_to(root).as_posix()] = content[:2_500]
                    break
            if result:
                return result

        for path in root.rglob("*"):
            if not path.is_file() or any(part in blocked_dirs for part in path.parts):
                continue
            if path.suffix.lower() not in allowed_suffixes and path.name not in {"Dockerfile", "Makefile"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            rel = path.relative_to(root).as_posix()
            lower_rel = rel.lower()
            lower_content = content.lower()
            score = 200 if rel in preferred_set else 0
            score += sum(20 for term in task_terms if term in lower_rel)
            score += min(60, sum(min(3, lower_content.count(term)) * 5 for term in task_terms))
            if endpoint_task and rel in {"app/main.py", "main.py", "src/main.py"}:
                score += 300
            if endpoint_task and rel.startswith("tests/") and any(key in lower_rel for key in ("api", "main", "endpoint", "route")):
                score += 120
            if rel.startswith("tests/"):
                score += 10
                if endpoint_task and ("client" in lower_content or "fastapi" in lower_content or "http" in lower_content):
                    score += 35
            candidates.append((path, content, score))

        result: dict[str, str] = {}
        total = 0
        for path, content, _ in sorted(candidates, key=lambda item: (-item[2], len(item[0].as_posix()), item[0].as_posix())):
            if len(result) >= 3 or total >= 14_000:
                break
            if len(content) > 8_000:
                content = content[:8_000] + "\n# ... truncated ..."
            rel = path.relative_to(root).as_posix()
            if total + len(content) > 14_000 and result:
                continue
            result[rel] = content
            total += len(content)
        return result
