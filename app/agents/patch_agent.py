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
    find: str | None = None
    replace: str | None = None
    content: str | None = None
    anchor: str | None = None
    insert_before: str | None = None
    insert_after: str | None = None


@dataclass
class PatchPlan:
    summary: str
    edits: list[FileEdit]


SYSTEM_PROMPT = """You are a software patch planner. Return JSON only.
Schema: {"summary":"short summary","edits":[{"path":"relative/path","find":"exact existing text","replace":"replacement text"}]}
For insertion into an existing file, prefer {"path":"relative/path","anchor":"short exact existing text","insert_after":"new text"} or insert_before. For a new file only, use {"path":"relative/path","content":"complete file content"}.
Rules:
- Prefer small exact find/replace edits over full-file rewrites.
- Treat test_feedback as mandatory correction instructions; do not repeat a rejected change.
- Implement every explicit acceptance criterion in the task, not merely a related change.
- The find text must match exactly once in the provided file.
- Only edit files necessary for the task.
- Paths must be relative to the repository root.
- Never write .env, credentials, .git contents, binary files, or files outside the repository.
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
        data = self._parse_model_response(raw)

        if not isinstance(data, dict) or not isinstance(data.get("edits"), list):
            raise PatchPlanError("Model response does not match patch schema")

        edits: list[FileEdit] = []
        total = 0
        for item in data["edits"]:
            if not isinstance(item, dict):
                raise PatchPlanError("Invalid edit entry")
            path = self._validate_path(str(item.get("path", "")))
            find = item.get("find")
            replace = item.get("replace")
            content = item.get("content")
            anchor = item.get("anchor")
            insert_before = item.get("insert_before")
            insert_after = item.get("insert_after")
            if anchor is not None:
                if not isinstance(anchor, str) or not anchor or (insert_before is None) == (insert_after is None):
                    raise PatchPlanError(f"Anchor edit for {path} requires anchor and exactly one of insert_before/insert_after")
                insertion = insert_before if insert_before is not None else insert_after
                if not isinstance(insertion, str):
                    raise PatchPlanError(f"Insertion for {path} must be a string")
                total += len(anchor.encode("utf-8")) + len(insertion.encode("utf-8"))
                edits.append(FileEdit(path=path, anchor=anchor, insert_before=insert_before, insert_after=insert_after))
                continue
            if content is not None:
                if not isinstance(content, str):
                    raise PatchPlanError(f"Edit content for {path} must be a string")
                total += len(content.encode("utf-8"))
                edits.append(FileEdit(path=path, content=content))
                continue
            if not isinstance(find, str) or not isinstance(replace, str) or not find:
                raise PatchPlanError(f"Edit for {path} must contain non-empty find and string replace")
            total += len(find.encode("utf-8")) + len(replace.encode("utf-8"))
            edits.append(FileEdit(path=path, find=find, replace=replace))

        if not edits:
            raise PatchPlanError("Patch plan contains no edits")
        if len(edits) > self.max_files:
            raise PatchPlanError(f"Patch plan exceeds max files ({self.max_files})")
        if total > self.max_bytes:
            raise PatchPlanError(f"Patch plan exceeds max bytes ({self.max_bytes})")

        return PatchPlan(summary=str(data.get("summary", "Proposed code changes")), edits=edits)

    @staticmethod
    def _parse_model_response(raw: str) -> dict:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            # Small models often add prose before/after otherwise-valid JSON.
            # Extract only a balanced top-level JSON object; never guess/repair fields.
            candidate = PatchAgent._extract_json_object(text)
            if candidate is None:
                raise PatchPlanError("Model response was not valid JSON") from exc
            try:
                data = json.loads(candidate)
            except json.JSONDecodeError as nested_exc:
                raise PatchPlanError("Model response was not valid JSON") from nested_exc
        # Small/local models sometimes add one or more wrapper objects. Unwrap only
        # single-object envelopes and stop as soon as the required edits key appears.
        for _ in range(4):
            if isinstance(data, dict) and "edits" in data:
                break
            if isinstance(data, dict):
                nested = [value for value in data.values() if isinstance(value, dict)]
                if len(nested) == 1:
                    data = nested[0]
                    continue
            break
        return data

    @staticmethod
    def _extract_json_object(text: str) -> str | None:
        start = text.find("{")
        while start >= 0:
            depth = 0
            in_string = False
            escaped = False
            for index in range(start, len(text)):
                char = text[index]
                if in_string:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == '"':
                        in_string = False
                    continue
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return text[start:index + 1]
            start = text.find("{", start + 1)
        return None
    def apply(self, root: Path, plan: PatchPlan) -> list[str]:
        changed: list[str] = []
        root = root.resolve()
        for edit in plan.edits:
            target = (root / edit.path).resolve()
            if root not in target.parents and target != root:
                raise PatchPlanError(f"Path escapes repository: {edit.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if edit.content is not None:
                if target.exists():
                    raise PatchPlanError(f"Full content writes are only allowed for new files: {edit.path}")
                target.write_text(edit.content, encoding="utf-8")
            else:
                if not target.exists():
                    raise PatchPlanError(f"Cannot patch missing file: {edit.path}")
                current = target.read_text(encoding="utf-8")
                if edit.anchor is not None:
                    count = current.count(edit.anchor)
                    if count != 1:
                        raise PatchPlanError(f"Anchor text for {edit.path} must match exactly once, matched {count}")
                    insertion = edit.insert_before if edit.insert_before is not None else edit.insert_after
                    replacement = (insertion or "") + edit.anchor if edit.insert_before is not None else edit.anchor + (insertion or "")
                    target.write_text(current.replace(edit.anchor, replacement, 1), encoding="utf-8")
                    changed.append(edit.path)
                    continue
                count = current.count(edit.find or "")
                if count != 1:
                    raise PatchPlanError(f"Find text for {edit.path} must match exactly once, matched {count}")
                target.write_text(current.replace(edit.find or "", edit.replace or "", 1), encoding="utf-8")
            changed.append(edit.path)
        return changed

    @staticmethod
    def _validate_path(value: str) -> str:
        value = value.replace("\\", "/").strip()
        while value.startswith("./"):
            value = value[2:]
        if not value or value.startswith("/") or ".." in Path(value).parts:
            raise PatchPlanError(f"Unsafe path: {value!r}")
        blocked = {".env", ".git"}
        parts = Path(value).parts
        if any(p in blocked for p in parts):
            raise PatchPlanError(f"Blocked path: {value}")
        return value
