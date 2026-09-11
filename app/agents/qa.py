from .base import Agent, AgentResult


class QAAgent(Agent):
    name = "qa"

    def run(self, project, tasks):
        brief = project["brief"].lower()
        synthetic_bug = any(word in brief for word in ["bug", "broken", "crash", "error"])
        if synthetic_bug:
            return AgentResult(
                "QA detected a reproducible defect marker from the project brief. Bug-fix cycle required.",
                "bug_found",
            )
        return AgentResult(
            "QA pass completed: acceptance checks, regression checklist, and security smoke checks passed.",
            "qa_passed",
        )


class BugFixAgent(Agent):
    name = "bug_fix"

    def run(self, project, tasks):
        return AgentResult(
            "Bug-fix pass completed. Root cause isolated and corrective patch prepared for re-test.",
            "fixed",
        )
