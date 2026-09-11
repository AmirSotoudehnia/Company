from __future__ import annotations

import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.settings import settings
from app.workers.workspace import CommandResult, WorkspaceError


@dataclass(frozen=True)
class SandboxLimits:
    memory: str = "1g"
    cpus: str = "1.0"
    pids: int = 256
    network: str = "none"


class DockerSandbox:
    """Run repository test commands in an isolated, disposable Docker container.

    The workspace is mounted read/write because test tools may create caches and
    generated files. The container gets no GitHub/LLM credentials and, by
    default, no network access. The host Docker socket is never mounted.
    """

    def __init__(self, image: str | None = None, limits: SandboxLimits | None = None):
        self.image = image or settings.sandbox_image
        self.limits = limits or SandboxLimits(
            memory=settings.sandbox_memory,
            cpus=settings.sandbox_cpus,
            pids=settings.sandbox_pids,
            network=settings.sandbox_network,
        )

    def available(self) -> bool:
        try:
            proc = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                text=True,
                capture_output=True,
                timeout=10,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0

    def run(self, workspace: Path, command: str, timeout: int | None = None) -> CommandResult:
        root = workspace.resolve()
        if not root.exists() or not root.is_dir():
            raise WorkspaceError("Sandbox workspace does not exist")
        if not self.available():
            raise WorkspaceError("Docker is required for sandbox execution but is unavailable")

        argv = shlex.split(command)
        if not argv:
            raise WorkspaceError("Sandbox command is empty")

        docker_cmd = [
            "docker", "run", "--rm",
            "--network", self.limits.network,
            "--memory", self.limits.memory,
            "--cpus", self.limits.cpus,
            "--pids-limit", str(self.limits.pids),
            "--security-opt", "no-new-privileges:true",
            "--cap-drop", "ALL",
            "--read-only",
            "--tmpfs", "/tmp:rw,noexec,nosuid,size=256m",
            "--tmpfs", "/home/agent:rw,noexec,nosuid,size=64m",
            "--mount", f"type=bind,src={root},dst=/workspace,rw",
            "--workdir", "/workspace",
            "--user", settings.sandbox_user,
            "--env", "HOME=/home/agent",
            "--env", "PYTHONDONTWRITEBYTECODE=1",
            self.image,
            *argv,
        ]

        try:
            proc = subprocess.run(
                docker_cmd,
                text=True,
                capture_output=True,
                timeout=timeout or settings.command_timeout_seconds,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkspaceError(f"Sandbox command timed out: {command}") from exc

        return CommandResult(
            command=" ".join(docker_cmd),
            returncode=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )


def run_test_command(workspace: Path, command: str) -> CommandResult:
    """Choose the configured execution backend for repository tests."""
    mode = settings.execution_mode.lower().strip()
    if mode == "docker":
        return DockerSandbox().run(workspace, command)
    if mode == "local" and settings.allow_local_execution:
        import os
        try:
            proc = subprocess.run(
                shlex.split(command),
                cwd=str(workspace),
                text=True,
                capture_output=True,
                timeout=settings.command_timeout_seconds,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkspaceError(f"Command timed out: {command}") from exc
        return CommandResult(command, proc.returncode, proc.stdout, proc.stderr)
    raise WorkspaceError(
        "Unsafe execution configuration. Use EXECUTION_MODE=docker, or explicitly "
        "set ALLOW_LOCAL_EXECUTION=true for trusted development only."
    )
