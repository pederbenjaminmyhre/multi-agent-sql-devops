from pydantic import BaseModel
from src.models.agent_finding import AgentFinding


class ReviewReport(BaseModel):
    status: str  # "approved" or "rejected"
    iterations: int
    findings: list[AgentFinding]
    cleaned_sql: str
    documentation: str
    changelog: list[str]
