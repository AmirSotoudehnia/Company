from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AcceptanceResult:
    ok: bool
    feedback: str = ""


class AcceptanceReviewer:
    """Cheap deterministic acceptance checks before a branch may be pushed."""

    def review(self, root: Path, task: str, changed_files: list[str] | None = None) -> AcceptanceResult:
        text = task.lower()
        main = self._main_file(root)
        if main is None:
            return AcceptanceResult(True)
        source = main.read_text(encoding="utf-8")
        routes = set(re.findall(r'@app\.(?:get|post|put|patch|delete)\(["\']([^"\']+)', source))
        requested = set(re.findall(r'/(?:[a-z0-9_-]+)', text))
        requested.discard('/json')
        missing = sorted(path for path in requested if path not in routes)
        if missing:
            return AcceptanceResult(False, "Acceptance failed: missing requested route(s): " + ", ".join(missing))
        if changed_files is not None and any(word in text for word in ("test", "tests", "tested")):
            if not any(Path(path).name.startswith("test_") or "/tests/" in f"/{path}" for path in changed_files):
                return AcceptanceResult(False, "Acceptance failed: task requires automated tests, but no test file changed.")
        if "/version" in requested:
            if not re.search(r'(?m)^[A-Z_]*VERSION[A-Z_]*\s*=|__version__\s*=', source):
                return AcceptanceResult(False, "Acceptance failed: /version must source its value from a single application version constant.")
            if not re.search(r'@app\.get\(["\']/version["\']\)', source):
                return AcceptanceResult(False, "Acceptance failed: GET /version endpoint was not implemented.")
            if changed_files is not None and any(word in text for word in ("test", "tests", "tested")):
                test_sources = []
                for path in changed_files:
                    candidate = root / path
                    if candidate.is_file() and (candidate.name.startswith("test_") or "tests" in candidate.parts):
                        test_sources.append(candidate.read_text(encoding="utf-8", errors="ignore"))
                if not any("/version" in body for body in test_sources):
                    return AcceptanceResult(False, "Acceptance failed: tests do not cover /version.")
        return AcceptanceResult(True)

    @staticmethod
    def _main_file(root: Path) -> Path | None:
        for rel in ("app/main.py", "main.py", "src/main.py"):
            candidate = root / rel
            if candidate.is_file():
                return candidate
        return None
