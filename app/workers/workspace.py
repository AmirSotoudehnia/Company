from __future__ import annotations

import os
import shlex
import shutil
import stat
import time
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import settings


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class WorkspaceError(RuntimeError):
    pass


class RepositoryWorkspace:
    """Disposable git workspace. Credentials are used only for git transport."""

    def __init__(self, owner: str, repo: str, task_id: str, token: str | None = None):
        self.owner = owner
        self.repo = repo
        self.token = token
        safe_task = "".join(c for c in task_id if c.isalnum() or c in "-_")[:80] or "task"
        self.path = Path(settings.workspace_root) / f"{repo}-{safe_task}"

    def _remote_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}.git"

    def prepare(self, base_branch: str = "main") -> Path:
        if self.path.exists():
            shutil.rmtree(self.path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        result = self._run_git_transport(["git", "clone", "--depth", "1", "--branch", base_branch, self._remote_url(), str(self.path)])
        if not result.ok:
            raise WorkspaceError(result.stderr or result.stdout)
        return self.path

    def create_branch(self, branch_name: str) -> CommandResult:
        return self.run(["git", "checkout", "-b", branch_name])

    def run(self, command: list[str], timeout: int | None = None) -> CommandResult:
        if not self.path.exists():
            raise WorkspaceError("Workspace is not prepared")
        return self._run_external(command, cwd=self.path, timeout=timeout)

    def run_shell_command(self, command: str, timeout: int | None = None) -> CommandResult:
        return self.run(shlex.split(command), timeout=timeout)

    def changed_files(self) -> list[str]:
        result = self.run(["git", "status", "--porcelain"])
        return [line[3:] for line in result.stdout.splitlines() if len(line) > 3]

    def commit_and_push(self, branch_name: str, message: str) -> str:
        self.run(["git", "config", "user.name", "Agent Company Bot"])
        self.run(["git", "config", "user.email", "agent-company@local.invalid"])
        self.run(["git", "add", "-A"])
        commit = self.run(["git", "commit", "-m", message])
        if not commit.ok and "nothing to commit" not in (commit.stdout + commit.stderr).lower():
            raise WorkspaceError(commit.stderr or commit.stdout)
        push = self._run_git_transport(["git", "push", "origin", branch_name], cwd=self.path)
        if not push.ok:
            raise WorkspaceError(push.stderr or push.stdout)
        sha = self.run(["git", "rev-parse", "HEAD"])
        if not sha.ok:
            raise WorkspaceError(sha.stderr or sha.stdout)
        return sha.stdout.strip()


    def reset_changes(self) -> None:
        reset = self.run(["git", "reset", "--hard", "HEAD"])
        clean = self.run(["git", "clean", "-fd"])
        if not reset.ok or not clean.ok:
            raise WorkspaceError(reset.stderr or clean.stderr or reset.stdout or clean.stdout)

    def _run_git_transport(self, command: list[str], cwd: Path | None = None) -> CommandResult:
        token = self.token or settings.github_token
        if not token:
            return self._run_external(command, cwd=cwd)
        askpass = self.path.parent / f".askpass-{self.path.name}.bat"
        askpass.write_text("@echo off\r\nif /I \"%~1\"==\"Username for 'https://github.com': \" (echo x-access-token) else (echo %AGENT_GIT_TOKEN%)\r\n", encoding="utf-8")
        env = {"GIT_ASKPASS": str(askpass), "GIT_TERMINAL_PROMPT": "0", "AGENT_GIT_TOKEN": token}
        try:
            return self._run_external(command, cwd=cwd, extra_env=env)
        finally:
            askpass.unlink(missing_ok=True)

    def cleanup(self) -> None:
        if not self.path.exists():
            return
        def onerror(func, path, exc_info):
            try:
                os.chmod(path, stat.S_IWRITE)
                func(path)
            except OSError:
                pass
        for attempt in range(3):
            try:
                shutil.rmtree(self.path, onerror=onerror)
                return
            except (PermissionError, OSError):
                if attempt == 2:
                    return
                time.sleep(0.2 * (attempt + 1))

    def _run_external(self, command: list[str], cwd: Path | None = None, timeout: int | None = None, extra_env: dict[str, str] | None = None) -> CommandResult:
        try:
            proc = subprocess.run(command, cwd=str(cwd) if cwd else None, text=True, capture_output=True, timeout=timeout or settings.command_timeout_seconds, env={**os.environ, "GIT_TERMINAL_PROMPT": "0", **(extra_env or {})})
        except subprocess.TimeoutExpired as exc:
            raise WorkspaceError(f"Command timed out: {' '.join(command)}") from exc
        return CommandResult(" ".join(command), proc.returncode, proc.stdout, proc.stderr)
