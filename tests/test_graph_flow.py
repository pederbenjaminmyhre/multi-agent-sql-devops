from unittest.mock import patch
import json
import pytest
from src.graph.builder import build_review_graph


def _make_fake_llm(responses: dict):
    """Return a factory that yields different responses based on call order."""
    call_count = {"n": 0}
    ordered_keys = list(responses.keys())

    class _FakeResponse:
        def __init__(self, content):
            self.content = content

    class _FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            idx = min(call_count["n"], len(ordered_keys) - 1)
            key = ordered_keys[idx]
            call_count["n"] += 1
            return _FakeResponse(json.dumps(responses[key]))

    return _FakeLLM()


@patch("src.graph.nodes.get_llm")
def test_full_graph_approved(mock_get_llm, bad_query_sql, schema_context):
    mock_get_llm.return_value = _make_fake_llm({
        "linter": {
            "findings": [{"severity": "warning", "message": "SELECT * used.", "line_ref": "6", "suggestion": "Use explicit columns."}],
            "cleaned_sql": "SET NOCOUNT ON;\nSELECT o.OrderID FROM Orders AS o;",
        },
        "performance": {
            "findings": [],
            "index_suggestions": [],
        },
        "doc_genie": {
            "documentation": "## GetCustomerOrders\nReturns orders.",
            "extended_properties_sql": [],
        },
        "skeptic": {
            "verdict": "approved",
            "reasoning": "Changes are safe.",
            "issues": [],
        },
    })

    graph = build_review_graph()
    result = graph.invoke({
        "sql_input": bad_query_sql,
        "schema_context": schema_context,
        "max_iterations": 3,
        "iteration": 0,
        "changelog_entries": [],
    })

    report = result["final_report"]
    assert report["status"] == "approved"
    assert report["iterations"] == 1
    assert "SET NOCOUNT ON" in report["cleaned_sql"]


@patch("src.graph.nodes.get_llm")
def test_full_graph_rejected_then_approved(mock_get_llm, bad_query_sql, schema_context):
    """Test critique-revise loop: skeptic rejects on first pass, approves on second."""
    call_count = {"n": 0}

    class _FakeResponse:
        def __init__(self, content):
            self.content = content

    responses = [
        # Pass 1: linter
        {"findings": [{"severity": "warning", "message": "SELECT * used."}], "cleaned_sql": "SELECT o.OrderID FROM Orders o;"},
        # Pass 1: performance
        {"findings": [], "index_suggestions": []},
        # Pass 1: doc_genie
        {"documentation": "", "extended_properties_sql": []},
        # Pass 1: skeptic REJECTS
        {"verdict": "rejected", "reasoning": "Missing NOCOUNT ON.", "issues": [{"severity": "warning", "message": "Missing SET NOCOUNT ON."}]},
        # Pass 2: linter (re-run)
        {"findings": [], "cleaned_sql": "SET NOCOUNT ON;\nSELECT o.OrderID FROM Orders AS o;"},
        # Pass 2: performance
        {"findings": [], "index_suggestions": []},
        # Pass 2: doc_genie
        {"documentation": "", "extended_properties_sql": []},
        # Pass 2: skeptic APPROVES
        {"verdict": "approved", "reasoning": "All good now.", "issues": []},
    ]

    class _FakeLLM:
        def bind_tools(self, tools):
            return self

        def invoke(self, messages):
            idx = min(call_count["n"], len(responses) - 1)
            call_count["n"] += 1
            return _FakeResponse(json.dumps(responses[idx]))

    mock_get_llm.return_value = _FakeLLM()

    graph = build_review_graph()
    result = graph.invoke({
        "sql_input": bad_query_sql,
        "schema_context": schema_context,
        "max_iterations": 3,
        "iteration": 0,
        "changelog_entries": [],
    })

    report = result["final_report"]
    assert report["status"] == "approved"
    assert report["iterations"] == 2
