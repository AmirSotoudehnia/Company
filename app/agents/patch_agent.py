from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.agents.llm import LLMClient


class PatchPlanError(ValueError):
    pass


@dataclass
class FileEdit:
    path: str
    content: str


@dataclass
class PatchPlan:
    summary: str
    edits: list[FileEdit]


SYSTEM_PROMPT = """You are a software patch planner. Return JSON only.
Schema: {"summary":"short summary","edits":[{"path":"relative/path","content":"complete replacement UTF-8 file content"}]}
Rules:
- Only edit files necessary for the task.
- Paths must be relative to the repository root.
- Never write .env, credentials, .git contents, binary files, or files outside the repository.
- Return complete file contents, not diffs.
- Do not include markdown fences.
"""


class PatchAgent:
    def __init__(self, client: LLMClient | None = None, max_files: int = 8, max_bytes: int = 250_000):
        self.client = client or LLMClient()
        self.max_files = max_files
        self.max_bytes = max_bytes

    def propose(self, task: str, context: dict[str, str], test_feedback: str = "") -> PatchPlan:
        payload = {
            "task": task,
            "files": context,
            "test_feedback": test_feedback[-12_000:],
        }
        raw = self.client.complete(SYSTEM_PROMPT, json.dumps(payload, ensure_ascii=False))
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PatchPlanError("Model response was not valid JSON") from exc

        if not isinstance(data, dict) or not isinstance(data.get("edits"), list):
            raise PatchPlanError("Model response does not match patch schema")

        edits: list[FileEdit] = []
        total = 0
        for item in data["edits"]:
            if not isinstance(item, dict):
                raise PatchPlanError("Invalid edit entry")
            path = self._validate_path(str(item.get("path", "")))
            content = item.get("content")
            if not isinstance(content, str):
                raise PatchPlanError(f"Edit content for {path} must be a string")
            total += len(content.encode("utf-8"))
            edits.append(FileEdit(path=path, content=content))

        if not edits:
            raise PatchPlanError("Patch plan contains no edits")
        if len(edits) > self.max_files:
            raise PatchPlanError(f"Patch plan exceeds max files ({self.max_files})")
        if total > self.max_bytes:
            raise PatchPlanError(f"Patch plan exceeds max bytes ({self.max_bytes})")

        return PatchPlan(summary=str(data.get("summary", "Proposed code changes")), edits=edits)

    def apply(self, root: Path, plan: PatchPlan) -> list[str]:
        changed: list[str] = []
        root = root.resolve()
        for edit in plan.edits:
            target = (root / edit.path).resolve()
            if root not in target.parents and target != root:
                raise PatchPlanError(f"Path escapes repository: {edit.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(edit.content, encoding="utf-8")
            changed.append(edit.path)
        return changed

    @staticmethod
    def _validate_path(value: str) -> str:
        value = value.replace("\\", "/").strip().lstrip("./")
        if not value or value.startswith("/") or ".." in Path(value).parts:
            raise PatchPlanError(f"Unsafe path: {value!r}")
        blocked = {".env", ".git"}
        parts = Path(value).parts
        if any(p in blocked for p in parts):
            raise PatchPlanError(f"Blocked path: {value}")
        return value
