from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from .base import Agent, AgentResult

@dataclass(frozen=True)
class ArchitecturePlan:
    stack: list[str]
    entrypoints: list[str]
    test_locations: list[str]
    constraints: list[str]
    implementation_order: list[str]

class ArchitectAgent(Agent):
    name = "architect"
    def inspect(self, root: Path | None = None) -> ArchitecturePlan:
        root = root or Path(".")
        stack = []
        for marker, name in (("pyproject.toml","python"),("requirements.txt","python"),("package.json","node"),("pubspec.yaml","flutter"),("build.gradle","gradle"),("build.gradle.kts","gradle")):
            if (root / marker).exists() and name not in stack: stack.append(name)
        entrypoints = [p for p in ("app/main.py","main.py","src/main.py") if (root / p).is_file()]
        tests = [p.relative_to(root).as_posix() for p in sorted((root / "tests").glob("test_*.py"))][:20] if (root / "tests").is_dir() else []
        return ArchitecturePlan(stack or ["unknown"], entrypoints, tests, ["preserve public interfaces", "keep changes minimal", "tests before delivery"], ["inspect", "implement", "test", "review"])
    def run(self, project, tasks):
        return AgentResult(json.dumps(asdict(self.inspect()), ensure_ascii=False), "planned")
