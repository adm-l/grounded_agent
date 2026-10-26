
import logging
import json
import sys

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from ollama import AsyncClient

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from app.tools import (
    check_payment_service_health,
    get_order_status,
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI(title="AI Agent Learning Project")

ollama = AsyncClient(host="http://localhost:11434")

MODEL = "llama3.2:3b"
MAX_ITERATIONS = 5


class ChatRequest(BaseModel):
    question: str


LOCAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "check_payment_service_health",
            "description": "Check the configured payment service health endpoint.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_order_status",
            "description": "Look up an order by its order ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "string",
                        "description": "Order ID, such as ORD-1001",
                    }
                },
                "required": ["order_id"],
            },
        },
    },
]


def serialize_mcp_result(result) -> dict:
    """Convert an MCP tool result into JSON-compatible data."""
    return {
        "is_error": result.isError,
        "content": [
            item.text if hasattr(item, "text") else str(item)
            for item in result.content
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat")
async def chat(request: ChatRequest):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a backend investigation assistant. "
                "Use available tools when relevant. "
                "Use search_logs for application log investigations. "
                "Never claim a tool succeeded without its actual result."
            ),
        },
        {"role": "user", "content": request.question},
    ]

    tool_results = []

    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
    )

    try:
        # Start the MCP server and establish a client session.
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Discover tools from the MCP server.
                mcp_response = await session.list_tools()

                mcp_tools = [
                    {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description or "",
                            "parameters": tool.inputSchema,
                        },
                    }
                    for tool in mcp_response.tools
                ]

                # Combine local tools with MCP-discovered tools.
                available_tools = LOCAL_TOOLS + mcp_tools

                for iteration in range(MAX_ITERATIONS):
                    response = await ollama.chat(
                        model=MODEL,
                        messages=messages,
                        tools=available_tools,
                    )

                    messages.append(response.message)
                    tool_calls = response.message.tool_calls or []

                    if not tool_calls:
                        return {
                            "answer": response.message.content,
                            "tool_results": tool_results,
                            "iterations": iteration + 1,
                        }

                    for call in tool_calls:
                        name = call.function.name
                        arguments = call.function.arguments or {}
                        print(f"DEBUG tool={name}, arguments={arguments}", flush=True)
                        if name == "check_payment_service_health":
                            result = await check_payment_service_health()

                        elif name == "get_order_status":
                            order_id = arguments.get("order_id", "")
                            if not order_id:
                                result = {"error": "Missing order_id"}
                            else:
                                result = await get_order_status(order_id)

                        elif any(
                            tool.name == name
                            for tool in mcp_response.tools
                        ):
                            # Execute the discovered tool through MCP.
                            mcp_result = await session.call_tool(
                                name,
                                arguments=arguments,
                            )
                            result = serialize_mcp_result(mcp_result)

                        else:
                            result = {"error": "Unknown tool"}

                        tool_results.append({
                            "tool": name,
                            "result": result,
                        })

                        messages.append({
                            "role": "tool",
                            "tool_name": name,
                            "content": json.dumps(result),
                        })

                return {
                    "answer": "Agent reached its iteration limit.",
                    "tool_results": tool_results,
                    "iterations": MAX_ITERATIONS,
                }

    except Exception as exc:
        logger.exception("Agent execution failed")

        raise HTTPException(
            status_code=502,
            detail=f"Agent execution failed: {type(exc).__name__}: {exc}",
        ) from exc
