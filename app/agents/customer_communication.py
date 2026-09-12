from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationDraft:
    kind: str
    subject: str
    body: str


class CustomerCommunicationAgent:
    """Draft-only customer communication; outbound sending is a separate human-approved action."""

    def draft_status(self, customer: str, project: str, status: str, milestones: list[dict]) -> CommunicationDraft:
        completed = [m['title'] for m in milestones if m['status'] == 'completed']
        body = f"Hello {customer},\n\nProject: {project}\nCurrent status: {status}."
        if completed:
            body += "\nCompleted milestones: " + ", ".join(completed) + "."
        body += "\n\nThis is a draft update pending human approval before sending."
        return CommunicationDraft('status_update', f"Status update: {project}", body)

    def draft_question(self, customer: str, project: str, question: str) -> CommunicationDraft:
        return CommunicationDraft('customer_question', f"Question about {project}", f"Hello {customer},\n\n{question}\n\nPending human approval before sending.")
