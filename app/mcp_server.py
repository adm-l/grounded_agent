
from mcp.server.fastmcp import FastMCP

from app.logs_data import SAMPLE_LOGS

mcp = FastMCP("local-log-tools")


@mcp.tool()
def search_logs(
    keyword: str = "",
    service: str = "",
    level: str = "",
    request_id: str = "",
) -> dict:
    """Search sample logs by keyword, service, level, or request ID."""

    results = []

    for log in SAMPLE_LOGS:
        if service and service.lower() not in log["service"].lower():
            continue

        if level and level.lower() != log["level"].lower():
            continue

        if request_id and request_id.lower() != log["request_id"].lower():
            continue

        searchable_text = " ".join(
            [
                log["service"],
                log["level"],
                log["request_id"],
                log["message"],
            ]
        ).lower()

        if keyword:
            terms = keyword.lower().split()
            if not all(term in searchable_text for term in terms):
                continue

        results.append(log)

    return {"count": len(results), "logs": results[:20]}

if __name__ == "__main__":
    mcp.run(transport="stdio")