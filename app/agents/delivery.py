from .base import Agent, AgentResult


class DeliveryAgent(Agent):
    name = "delivery"

    def run(self, project, tasks):
        return AgentResult(
            "Release package prepared with changelog, validation notes, and deployment checklist. Human production approval required.",
            "awaiting_delivery_approval",
        )
