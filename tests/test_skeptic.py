from src.agents.skeptic import run_skeptic
from src.models.agent_finding import AgentFinding, Severity


def _sample_findings():
    return [
        AgentFinding(severity=Severity.ERROR, agent="linter", message="SELECT * used."),
        AgentFinding(severity=Severity.WARNING, agent="performance", message="Missing index."),
    ]


def test_skeptic_approves(fake_skeptic_approved_llm, bad_query_sql):
    result = run_skeptic(
        fake_skeptic_approved_llm,
        original_sql=bad_query_sql,
        cleaned_sql="SELECT o.OrderID FROM Orders o;",
        findings=_sample_findings(),
        index_suggestions=["CREATE INDEX IX_Test ON Orders(Status);"],
    )
    assert result["verdict"] == "approved"
    assert len(result["issues"]) == 0


def test_skeptic_rejects(fake_skeptic_rejected_llm, bad_query_sql):
    result = run_skeptic(
        fake_skeptic_rejected_llm,
        original_sql=bad_query_sql,
        cleaned_sql="SELECT o.OrderID FROM Orders o WITH (NOLOCK);",
        findings=_sample_findings(),
        index_suggestions=[],
    )
    assert result["verdict"] == "rejected"
    assert len(result["issues"]) == 1
