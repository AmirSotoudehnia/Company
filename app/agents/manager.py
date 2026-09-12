from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from .base import Agent, AgentResult

@dataclass(frozen=True)
class ProjectPlan:
    objective: str
    acceptance_criteria: list[str]
    workstreams: list[str]
    risks: list[str]

class ProjectManagerAgent(Agent):
    name = "project_manager"
    def plan(self, project: dict) -> ProjectPlan:
        brief = project["brief"].strip()
        criteria = ["Implement requested behavior without unrelated changes.", "Add or update automated tests for changed behavior.", "Existing regression tests must pass before delivery."]
        risks = [] if project.get("risk_level", "normal") == "normal" else [f"Project risk level is {project['risk_level']}; require extra review."]
        return ProjectPlan(brief[:500], criteria, ["architecture", "implementation", "qa", "delivery"], risks)
    def run(self, project, tasks):
        return AgentResult(json.dumps(asdict(self.plan(project)), ensure_ascii=False), "pm_planned")
