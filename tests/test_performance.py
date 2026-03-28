from src.agents.performance import run_performance


def test_performance_detects_missing_index(fake_performance_llm, bad_query_sql, schema_context):
    result = run_performance(fake_performance_llm, bad_query_sql, schema_context)
    assert len(result["findings"]) == 1
    assert "not indexed" in result["findings"][0].message.lower()


def test_performance_returns_index_suggestions(fake_performance_llm, bad_query_sql, schema_context):
    result = run_performance(fake_performance_llm, bad_query_sql, schema_context)
    assert len(result["index_suggestions"]) == 1
    assert "CREATE INDEX" in result["index_suggestions"][0]
