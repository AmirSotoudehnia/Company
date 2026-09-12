from __future__ import annotations

import re
from pathlib import Path


class DeterministicEditError(ValueError):
    pass


class DeterministicEditor:
    """Apply narrow, auditable edits for acceptance patterns we understand."""

    def apply(self, root: Path, task: str) -> list[str]:
        text = task.lower()
        if "/version" in text and any(word in text for word in ("endpoint", "route", "get")):
            return self._ensure_version_endpoint(root, text)
        return []

    @staticmethod
    def _main_file(root: Path) -> Path:
        for rel in ("app/main.py", "main.py", "src/main.py"):
            path = root / rel
            if path.is_file():
                return path
        raise DeterministicEditError("FastAPI entrypoint not found")
    def _ensure_version_endpoint(self, root: Path, task_text: str) -> list[str]:
        main = self._main_file(root)
        source = main.read_text(encoding="utf-8")
        changed: list[str] = []
        version_match = re.search(r'FastAPI\([^\n]*version=["\']([^"\']+)["\']', source)
        constant_match = re.search(r'(?m)^APP_VERSION\s*=\s*["\']([^"\']+)["\']', source)
        if version_match:
            version = version_match.group(1)
        elif constant_match and "version=APP_VERSION" in source:
            version = constant_match.group(1)
        else:
            raise DeterministicEditError("Existing FastAPI version source not found")
        if not re.search(r'(?m)^APP_VERSION\s*=', source):
            import_end = source.find("\n\n", source.find("from fastapi"))
            if import_end < 0:
                raise DeterministicEditError("Safe version constant insertion point not found")
            source = source[:import_end + 2] + f'APP_VERSION = "{version}"\n\n' + source[import_end + 2:]
        source = re.sub(
            r'(FastAPI\([^\n]*?version=)["\'][^"\']+["\']',
            r'\1APP_VERSION', source, count=1,
        )
        source = source.replace('"version": app.version', '"version": APP_VERSION')
        if not re.search(r'@app\.get\(["\']/version["\']\)', source):
            marker = '@app.get("/health")'
            pos = source.find(marker)
            if pos < 0:
                raise DeterministicEditError("Safe route insertion point not found")
            block = '@app.get("/version")\ndef version():\n    return {"version": APP_VERSION}\n\n\n'
            source = source[:pos] + block + source[pos:]
        main.write_text(source, encoding="utf-8")
        changed.append(main.relative_to(root).as_posix())
        if "test" in task_text:
            changed.extend(self._ensure_version_test(root))
        return list(dict.fromkeys(changed))
    @staticmethod
    def _ensure_version_test(root: Path) -> list[str]:
        tests = root / "tests"
        tests.mkdir(exist_ok=True)
        for path in sorted(tests.glob("test_*.py")):
            content = path.read_text(encoding="utf-8")
            if "TestClient" in content and "/health" in content:
                if "/version" not in content:
                    content += (
                        "\n\ndef test_version_endpoint():\n"
                        "    response = client.get(\"/version\")\n"
                        "    assert response.status_code == 200\n"
                        "    assert response.json()[\"version\"]\n"
                    )
                    path.write_text(content, encoding="utf-8")
                return [path.relative_to(root).as_posix()]
        path = tests / "test_version_endpoint.py"
        path.write_text(
            'from fastapi.testclient import TestClient\n\n'
            'from app.main import APP_VERSION, app\n\n'
            'client = TestClient(app)\n\n'
            'def test_version_endpoint():\n'
            '    response = client.get("/version")\n'
            '    assert response.status_code == 200\n'
            '    assert response.json() == {"version": APP_VERSION}\n',
            encoding="utf-8",
        )
        return [path.relative_to(root).as_posix()]
