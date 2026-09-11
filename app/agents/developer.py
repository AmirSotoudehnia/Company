from .base import Agent, AgentResult


class DeveloperAgent(Agent):
    name = "developer"

    def run(self, project, tasks):
        todo = [t for t in tasks if t["role"] == "developer" and t["status"] != "done"]
        if not todo:
            return AgentResult("No pending development tasks.", "development_done")
        titles = ", ".join(t["title"] for t in todo)
        return AgentResult(
            "Implementation pass completed for: " + titles + ". Code is ready for automated QA.",
            "development_done",
        )
