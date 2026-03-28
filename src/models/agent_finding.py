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


# Map non-standard LLM severity strings to our enum
_SEVERITY_MAP = {
    "error": Severity.ERROR,
    "critical": Severity.ERROR,
    "high": Severity.ERROR,
    "warning": Severity.WARNING,
    "medium": Severity.WARNING,
    "warn": Severity.WARNING,
    "info": Severity.INFO,
    "low": Severity.INFO,
    "informational": Severity.INFO,
}


def normalize_severity(raw: str) -> Severity:
    return _SEVERITY_MAP.get(raw.lower().strip(), Severity.WARNING)
