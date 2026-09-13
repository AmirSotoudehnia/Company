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


class AutonomousCodeRequest(BaseModel):
    issue_number: int
    branch: str | None = None
    max_attempts: int = Field(default=3, ge=1, le=5)


class TenantBootstrap(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=60)


class InstallationRegister(BaseModel):
    installation_id: int = Field(gt=0)
    account_login: str = Field(min_length=1, max_length=120)
    account_type: str = Field(default="User", max_length=40)


class RepositoryRegister(BaseModel):
    installation_id: int = Field(gt=0)
    owner: str = Field(min_length=1, max_length=120)
    name: str = Field(min_length=1, max_length=120)
    default_branch: str = Field(default="main", min_length=1, max_length=120)
    auto_code_enabled: bool = True
    max_attempts: int = Field(default=3, ge=1, le=5)
    test_command: str = Field(default="python -m pytest -q", min_length=1, max_length=300)
    required_label: str = Field(default="agent:run", min_length=1, max_length=80)


class CodeJobRequest(BaseModel):
    issue_number: int = Field(gt=0)


class OpportunityCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    brief: str = Field(min_length=10)
    source: str = Field(default="manual", min_length=1, max_length=80)
    source_url: str = Field(default="", max_length=500)
    budget: float | None = Field(default=None, ge=0)


class SalesApprovalDecision(BaseModel):
    approved: bool
    note: str = ""


class MilestoneInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    deliverable: str = Field(min_length=2)
    due_date: str | None = None


class CustomerIntake(BaseModel):
    opportunity_id: int = Field(gt=0)
    customer_name: str = Field(min_length=2, max_length=160)
    email: str = Field(default="", max_length=200)
    company: str = Field(default="", max_length=160)
    scope: str = Field(min_length=10)
    acceptance_criteria: list[str] = Field(min_length=1)
    milestones: list[MilestoneInput] = Field(min_length=1)
    budget: float | None = Field(default=None, ge=0)
    deadline: str | None = None


class ChangeRequestCreate(BaseModel):
    description: str = Field(min_length=5)
    budget_delta: float = 0
    deadline_delta_days: int = 0


class OpsCheckCreate(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    target: str = Field(min_length=1, max_length=300)
    healthy: bool
    detail: str = Field(default="", max_length=1000)
