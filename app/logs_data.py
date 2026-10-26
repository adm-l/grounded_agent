
SAMPLE_LOGS = [
    {
        "timestamp": "2026-10-27T09:00:00",
        "service": "payment-service",
        "level": "INFO",
        "request_id": "REQ-1001",
        "message": "Payment request started",
    },
    {
        "timestamp": "2026-10-27T09:00:01",
        "service": "payment-service",
        "level": "ERROR",
        "request_id": "REQ-1002",
        "message": "Payment gateway connection timed out",
    },
    {
        "timestamp": "2026-10-27T09:00:02",
        "service": "order-service",
        "level": "ERROR",
        "request_id": "REQ-1003",
        "message": "Failed to create order: inventory unavailable",
    },
    {
        "timestamp": "2026-10-27T09:00:03",
        "service": "payment-service",
        "level": "WARN",
        "request_id": "REQ-1004",
        "message": "Payment retry scheduled",
    },
    {
        "timestamp": "2026-10-27T09:00:04",
        "service": "order-service",
        "level": "INFO",
        "request_id": "REQ-1005",
        "message": "Order created successfully",
    },
]
