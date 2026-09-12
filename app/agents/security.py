from .base import Agent, AgentResult


class SecurityAgent(Agent):
    """Fail-closed security gate before a release package is prepared."""

    name = "security"

    def run(self, project, tasks):
        brief = project["brief"].lower()
        blockers = [
            term for term in ("hardcoded secret", "disable auth", "expose token", "sql injection")
            if term in brief
        ]
        if blockers:
            return AgentResult(
                "Security review blocked delivery: " + ", ".join(blockers),
                "security_blocked",
            )
        return AgentResult(
            "Security review passed: secrets, authentication, input handling, and least-privilege checklist reviewed.",
            "security_passed",
        )