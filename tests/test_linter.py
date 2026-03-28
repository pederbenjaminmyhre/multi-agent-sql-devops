from src.agents.linter import run_linter


def test_linter_detects_findings(fake_linter_llm, bad_query_sql):
    result = run_linter(fake_linter_llm, bad_query_sql)
    assert len(result["findings"]) == 2
    assert result["findings"][0].severity.value == "error"
    assert "SELECT *" in result["findings"][0].message


def test_linter_returns_cleaned_sql(fake_linter_llm, bad_query_sql):
    result = run_linter(fake_linter_llm, bad_query_sql)
    assert "SET NOCOUNT ON" in result["cleaned_sql"]
    assert "SELECT *" not in result["cleaned_sql"]
