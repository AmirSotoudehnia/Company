from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    brief: str = Field(min_length=10)
    risk_level: str = "normal"


class ApprovalDecision(BaseModel):
    approved: bool
    note: str = ""


class GitHubImport(BaseModel):
    issue_number: int
