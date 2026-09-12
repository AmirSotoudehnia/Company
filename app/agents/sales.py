from dataclasses import dataclass

from .opportunity import OpportunityAssessment


@dataclass
class SalesProposal:
    status: str
    subject: str
    proposal: str


class SalesAgent:
    """Drafts proposals only; sending/commitment remains a human gate."""

    def draft(self, title: str, brief: str, assessment: OpportunityAssessment) -> SalesProposal:
        if assessment.decision != "qualified":
            return SalesProposal("not_ready", title, "Opportunity requires human qualification before outreach.")
        proposal = (
            f"Proposal for {title}\n\n"
            f"We can deliver this work through a staged engineering process: planning, architecture, "
            f"implementation, QA, code review, security review, and delivery.\n\n"
            f"Understanding: {brief.strip()}\n\n"
            "Any scope, price, deadline, customer commitment, or outbound message requires human approval before sending."
        )
        return SalesProposal("awaiting_human_approval", f"Proposal: {title}", proposal)