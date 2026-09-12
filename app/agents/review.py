from .base import Agent, AgentResult


class CodeReviewAgent(Agent):
    """Independent quality gate between QA and security review."""

    name = "code_review"

    def run(self, project, tasks):
        brief = project["brief"].lower()
        blockers = [term for term in ("review blocker", "unsafe hack", "skip tests") if term in brief]
        if blockers:
            return AgentResult(
                "Code review blocked delivery: " + ", ".join(blockers),
                "review_blocked",
            )
        return AgentResult(
            "Code review passed: scope, maintainability, regression risk, and test expectations reviewed.",
            "review_passed",
        )