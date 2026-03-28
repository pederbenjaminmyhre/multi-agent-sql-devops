from enum import Enum
from pydantic import BaseModel


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class AgentFinding(BaseModel):
    severity: Severity
    agent: str
    message: str
    line_ref: str | None = None
    suggestion: str | None = None
