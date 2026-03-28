from typing import TypedDict
from src.models.agent_finding import AgentFinding


class ReviewState(TypedDict, total=False):
    # Input
    sql_input: str
    schema_context: dict | None
    max_iterations: int

    # Linter output
    linter_findings: list[AgentFinding]
    cleaned_sql: str

    # Performance output
    performance_findings: list[AgentFinding]
    index_suggestions: list[str]

    # Doc-Genie output
    documentation: str
    extended_properties_sql: list[str]

    # Skeptic output
    skeptic_verdict: str  # "approved" | "rejected"
    skeptic_reasoning: str
    skeptic_issues: list[AgentFinding]

    # Loop tracking
    iteration: int
    changelog_entries: list[str]

    # Final
    final_report: dict
