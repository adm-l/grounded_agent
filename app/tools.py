
import os

import httpx


PAYMENT_SERVICE_URL = os.getenv(
    "PAYMENT_SERVICE_URL",
    "http://localhost:8004/health",
)


async def check_payment_service_health() -> dict:
    """Check the health endpoint of the configured payment service."""

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(PAYMENT_SERVICE_URL)

        return {
            "reachable": True,
            "status_code": response.status_code,
            "healthy": response.is_success,
            "body": response.text[:500],
        }

    except httpx.HTTPError as exc:
        return {
            "reachable": False,
            "healthy": False,
            "error": type(exc).__name__,
        }



ORDERS = {
    "ORD-1001": {
        "order_id": "ORD-1001",
        "status": "shipped",
        "amount": 1250,
    },
    "ORD-1002": {
        "order_id": "ORD-1002",
        "status": "processing",
        "amount": 800,
    },
}


async def get_order_status(order_id: str) -> dict:
    """Look up an order in the sample order dataset."""

    order = ORDERS.get(order_id.upper())

    if order is None:
        return {
            "found": False,
            "order_id": order_id,
            "message": "Order not found",
        }

    return {
        "found": True,
        **order,
    }
