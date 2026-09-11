from dataclasses import dataclass


@dataclass
class AgentResult:
    summary: str
    next_status: str | None = None


class Agent:
    name = "agent"

    def run(self, project: dict, tasks: list[dict]) -> AgentResult:
        raise NotImplementedError
