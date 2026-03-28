import json
from pathlib import Path
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def bad_query_sql() -> str:
    return (FIXTURES_DIR / "bad_query.sql").read_text(encoding="utf-8")


@pytest.fixture
def good_query_sql() -> str:
    return (FIXTURES_DIR / "good_query.sql").read_text(encoding="utf-8")


@pytest.fixture
def schema_context() -> dict:
    return json.loads((FIXTURES_DIR / "schema.json").read_text(encoding="utf-8"))


class FakeLLMResponse:
    """Minimal stand-in for an LLM response with .content attribute."""

    def __init__(self, content: str):
        self.content = content


class FakeLLM:
    """Deterministic mock LLM that returns a pre-set JSON response."""

    def __init__(self, response_json: dict):
        self._response = json.dumps(response_json)

    def bind_tools(self, tools):
        return self

    def invoke(self, messages):
        return FakeLLMResponse(self._response)


@pytest.fixture
def fake_linter_llm():
    return FakeLLM({
        "findings": [
            {
                "severity": "error",
                "message": "SELECT * used — specify explicit columns.",
                "line_ref": "6",
                "suggestion": "Replace SELECT * with explicit column list.",
            },
            {
                "severity": "warning",
                "message": "Missing SET NOCOUNT ON in stored procedure.",
                "line_ref": "1",
                "suggestion": "Add SET NOCOUNT ON after AS.",
            },
        ],
        "cleaned_sql": "SET NOCOUNT ON;\n\nSELECT o.OrderID, o.OrderDate\nFROM Orders AS o;",
    })


@pytest.fixture
def fake_performance_llm():
    return FakeLLM({
        "findings": [
            {
                "severity": "warning",
                "message": "JOIN on OrderItems.OrderID is not indexed.",
                "line_ref": "9",
                "suggestion": "CREATE INDEX IX_OrderItems_OrderID ON OrderItems(OrderID);",
            },
        ],
        "index_suggestions": [
            "CREATE INDEX IX_OrderItems_OrderID ON OrderItems(OrderID);",
        ],
    })


@pytest.fixture
def fake_doc_genie_llm():
    return FakeLLM({
        "documentation": "## dbo.GetCustomerOrders\n\nStored procedure that retrieves orders for a given customer.",
        "extended_properties_sql": [
            "EXEC sp_addextendedproperty @name=N'MS_Description', @value=N'Retrieves customer orders', @level0type=N'SCHEMA', @level0name=N'dbo', @level1type=N'PROCEDURE', @level1name=N'GetCustomerOrders';",
        ],
    })


@pytest.fixture
def fake_skeptic_approved_llm():
    return FakeLLM({
        "verdict": "approved",
        "reasoning": "All proposed changes are safe. No breaking changes detected.",
        "issues": [],
    })


@pytest.fixture
def fake_skeptic_rejected_llm():
    return FakeLLM({
        "verdict": "rejected",
        "reasoning": "The suggested NOLOCK hint on the Orders table could cause dirty reads in a financial context.",
        "issues": [
            {
                "severity": "warning",
                "message": "NOLOCK on Orders table may cause dirty reads for financial data.",
            },
        ],
    })
