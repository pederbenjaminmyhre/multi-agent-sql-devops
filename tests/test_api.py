from unittest.mock import patch, MagicMock
import json
import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app


@pytest.fixture
def mock_graph():
    """Mock the compiled graph so tests don't call a real LLM."""
    mock = MagicMock()
    mock.invoke.return_value = {
        "final_report": {
            "status": "approved",
            "iterations": 1,
            "findings": [
                {"severity": "warning", "agent": "linter", "message": "SELECT * used.", "line_ref": "6", "suggestion": "Use explicit columns."}
            ],
            "cleaned_sql": "SET NOCOUNT ON;\nSELECT o.OrderID FROM Orders AS o;",
            "documentation": "",
            "changelog": ["[Linter pass 1] SELECT * used."],
        }
    }
    return mock


@pytest.mark.asyncio
async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_review_endpoint(mock_graph):
    with patch("src.main._graph", mock_graph):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post("/review", json={
                "sql": "SELECT * FROM Orders;",
                "max_iterations": 2,
            })
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "approved"
    assert body["iterations"] == 1
    assert len(body["findings"]) == 1


@pytest.mark.asyncio
async def test_review_validates_empty_sql():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/review", json={"sql": ""})
    assert resp.status_code == 422
