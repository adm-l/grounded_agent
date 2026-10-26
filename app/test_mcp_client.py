
import asyncio
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def main():
    server = StdioServerParameters(
        command=sys.executable,
        args=["-m", "app.mcp_server"],
    )

    async with stdio_client(server) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            available = await session.list_tools()

            print("Available MCP tools:")
            for tool in available.tools:
                print(f"- {tool.name}: {tool.description}")

            result = await session.call_tool(
                "search_logs",
                arguments={
                    "service": "payment-service",
                    "level": "ERROR",
                },
            )

            print("\nSearch result:")
            for item in result.content:
                if hasattr(item, "text"):
                    print(item.text)


if __name__ == "__main__":
    asyncio.run(main())
