import json
from types import SimpleNamespace

from fastapi.testclient import TestClient

import app.main as agent_main


class FakeMCPResult:
    isError = False

    def __init__(self, payload):
        self.content = [SimpleNamespace(text=json.dumps(payload))]


class FakeMCPSession:
    def __init__(self, read=None, write=None):
        self.called_tools = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def initialize(self):
        return None

    async def list_tools(self):
        tool = SimpleNamespace(
            name="search_logs",
            description="Search sample application logs.",
            inputSchema={
                "type": "object",
                "properties": {"service": {"type": "string"}},
                "required": [],
            },
        )
        return SimpleNamespace(tools=[tool])

    async def call_tool(self, name, arguments):
        self.called_tools.append((name, arguments))
        return FakeMCPResult({
            "count": 1,
            "logs": [{
                "service": arguments.get("service", "payment-service"),
                "level": "ERROR",
                "request_id": "REQ-1002",
                "message": "Payment gateway connection timed out",
            }],
        })


class FakeStdioClient:
    async def __aenter__(self):
        return ("fake-read-stream", "fake-write-stream")

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def make_tool_call(name, arguments):
    return SimpleNamespace(
        role="assistant",
        content="",
        tool_calls=[
            SimpleNamespace(
                function=SimpleNamespace(name=name, arguments=arguments)
            )
        ],
    )


def make_final_message(content):
    return SimpleNamespace(role="assistant", content=content, tool_calls=[])


def test_chat_discovers_and_executes_mcp_tool(monkeypatch):
    session = FakeMCPSession()
    responses = [
        SimpleNamespace(message=make_tool_call(
            "search_logs", {"service": "payment-service"}
        )),
        SimpleNamespace(message=make_final_message(
            "The payment gateway request timed out."
        )),
    ]
    seen_tool_schemas = []

    async def fake_chat(**kwargs):
        seen_tool_schemas.append(kwargs["tools"])
        return responses.pop(0)

    monkeypatch.setattr(agent_main, "stdio_client", lambda params: FakeStdioClient())
    monkeypatch.setattr(agent_main, "ClientSession", lambda read, write: session)
    monkeypatch.setattr(agent_main.ollama, "chat", fake_chat)

    response = TestClient(agent_main.app).post(
        "/chat",
        json={"question": "Find payment-service errors."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "The payment gateway request timed out."
    assert payload["iterations"] == 2
    assert payload["tool_results"][0]["tool"] == "search_logs"
    assert payload["tool_results"][0]["result"]["is_error"] is False
    assert session.called_tools == [
        ("search_logs", {"service": "payment-service"})
    ]
    assert any(
        tool["function"]["name"] == "search_logs"
        for tool in seen_tool_schemas[0]
    )


def test_chat_returns_iteration_limit_when_model_never_finishes(monkeypatch):
    session = FakeMCPSession()
    calls = {"count": 0}

    async def fake_chat(**kwargs):
        calls["count"] += 1
        return SimpleNamespace(message=make_tool_call(
            "get_order_status", {"order_id": "ORD-1001"}
        ))

    monkeypatch.setattr(agent_main, "stdio_client", lambda params: FakeStdioClient())
    monkeypatch.setattr(agent_main, "ClientSession", lambda read, write: session)
    monkeypatch.setattr(agent_main.ollama, "chat", fake_chat)

    response = TestClient(agent_main.app).post(
        "/chat",
        json={"question": "Keep checking this order."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "Agent reached its iteration limit."
    assert payload["iterations"] == agent_main.MAX_ITERATIONS
    assert calls["count"] == agent_main.MAX_ITERATIONS
    assert len(payload["tool_results"]) == agent_main.MAX_ITERATIONS


def test_chat_handles_unknown_model_requested_tool(monkeypatch):
    session = FakeMCPSession()
    responses = [
        SimpleNamespace(message=make_tool_call("not_a_real_tool", {})),
        SimpleNamespace(message=make_final_message("I could not run that tool.")),
    ]

    async def fake_chat(**kwargs):
        return responses.pop(0)

    monkeypatch.setattr(agent_main, "stdio_client", lambda params: FakeStdioClient())
    monkeypatch.setattr(agent_main, "ClientSession", lambda read, write: session)
    monkeypatch.setattr(agent_main.ollama, "chat", fake_chat)

    response = TestClient(agent_main.app).post(
        "/chat",
        json={"question": "Use an unavailable tool."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["answer"] == "I could not run that tool."
    assert payload["tool_results"] == [
        {"tool": "not_a_real_tool", "result": {"error": "Unknown tool"}}
    ]
    assert session.called_tools == []
