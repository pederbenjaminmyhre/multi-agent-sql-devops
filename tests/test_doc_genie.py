from src.agents.doc_genie import run_doc_genie


def test_doc_genie_generates_docs(fake_doc_genie_llm, bad_query_sql):
    result = run_doc_genie(fake_doc_genie_llm, bad_query_sql)
    assert "GetCustomerOrders" in result["documentation"]
    assert len(result["extended_properties_sql"]) == 1
