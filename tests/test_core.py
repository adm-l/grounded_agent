import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.tools import get_order_status
from app.mcp_server import search_logs

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_known_order_lookup_is_case_insensitive():
    result = asyncio.run(get_order_status("ord-1001"))

    assert result == {
        "found": True,
        "order_id": "ORD-1001",
        "status": "shipped",
        "amount": 1250,
    }


def test_unknown_order_returns_not_found():
    result = asyncio.run(get_order_status("ORD-9999"))

    assert result["found"] is False
    assert result["order_id"] == "ORD-9999"
    assert result["message"] == "Order not found"


def test_log_search_filters_by_service_and_level():
    result = search_logs(service="PAYMENT", level="error")

    assert result["count"] == 1
    assert result["logs"][0]["request_id"] == "REQ-1002"


def test_log_search_filters_by_request_id():
    result = search_logs(request_id="req-1002")

    assert result["count"] == 1
    assert result["logs"][0]["message"] == "Payment gateway connection timed out"


def test_log_search_keyword_requires_all_terms():
    result = search_logs(keyword="payment timed out")

    assert result["count"] == 1
    assert result["logs"][0]["request_id"] == "REQ-1002"


def test_log_search_returns_empty_result_for_no_match():
    result = search_logs(service="unknown-service")

    assert result == {"count": 0, "logs": []}
