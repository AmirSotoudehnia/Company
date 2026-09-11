from .base import Agent, AgentResult


class ProjectManagerAgent(Agent):
    name = "project_manager"

    def run(self, project, tasks):
        brief = project["brief"].strip()
        summary = (
            "Scope parsed. Created implementation, QA, and delivery workstreams. "
            f"Primary brief: {brief[:220]}"
        )
        return AgentResult(summary=summary, next_status="planned")
