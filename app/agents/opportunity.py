from dataclasses import dataclass


@dataclass
class OpportunityAssessment:
    score: int
    decision: str
    reasons: list[str]
    risks: list[str]


class OpportunityAgent:
    """Scores inbound work before sales spends time on it."""

    def assess(self, title: str, brief: str, budget: float | None = None) -> OpportunityAssessment:
        text = f"{title} {brief}".lower()
        score = 50
        reasons, risks = [], []
        strengths = ("python", "api", "automation", "ai", "flutter", "android", "web", "github")
        matches = [item for item in strengths if item in text]
        if matches:
            score += min(30, len(matches) * 8)
            reasons.append("Capability match: " + ", ".join(matches))
        if budget is not None and budget > 0:
            score += 10
            reasons.append("Budget supplied")
        for marker in ("urgent", "production access", "credentials", "unlimited revisions"):
            if marker in text:
                score -= 10
                risks.append(marker)
        score = max(0, min(100, score))
        decision = "qualified" if score >= 60 else "needs_review"
        return OpportunityAssessment(score, decision, reasons or ["General software opportunity"], risks)