# Grounded Agent — AI Backend Investigation Agent

A learning project that combines **FastAPI**, a local **Ollama LLM**, Python tools, and an **MCP (Model Context Protocol)** server to investigate sample backend logs and answer questions about mock orders and service health.

The project is being built incrementally to learn how an agent works in practice. It currently uses local sample data; it does **not** require a database.

## 1. Current status

The following phases have been implemented and manually verified:

| Phase | Implementation | Status |
|---|---|---|
| 1 | FastAPI application with `GET /health` and `POST /chat` | Implemented |
| 2 | Ollama integration using `llama3.2:3b` | Implemented; requires local Ollama |
| 3 | Local Python tools for mock order lookup and a configured health endpoint | Implemented |
| 4 | Bounded agent loop with tool calling and a maximum of five iterations | Implemented |
| 5 | MCP stdio server exposing `search_logs`, plus a standalone MCP client test | Implemented |
| 6 | End-to-end log investigation through FastAPI → Ollama → MCP → sample logs | Manually verified |
| 7 | Automated regression tests with pytest | Planned; not implemented yet |
| 8 | Production hardening, packaging, observability and deployment | Planned |

Latest verified end-to-end example: the agent found payment log `REQ-1002`, whose message is `Payment gateway connection timed out`.

The log confirms a timeout occurred. It does not establish the underlying cause; network failure, gateway overload, and other causes are hypotheses until supported by more telemetry.

## 2. How the agent works

### Request flow

1. A client sends a question to `POST /chat`.
2. FastAPI creates the conversation messages, including instructions for the backend investigation assistant.
3. The application starts the MCP server as a subprocess using Python's current interpreter and connects to it over **stdio**.
4. The MCP client initializes its session and discovers tools exposed by the server.
5. The application combines MCP-discovered tools with local Python tools and passes their schemas to Ollama.
6. Ollama decides whether to answer directly or request a tool call.
7. The application executes the selected local tool or invokes the MCP tool through the MCP session.
8. The tool result is added to the conversation and sent back to the model for a final explanation.
9. The loop stops when the model returns a final answer or the five-iteration limit is reached.

### Architecture

```text
Client / curl
     |
     v
FastAPI: POST /chat
     |
     v
Agent loop (maximum 5 iterations) <----> Ollama API (localhost:11434)
     |
     +---- Local Python tools
     |       +-- check_payment_service_health
     |       +-- get_order_status (mock orders)
     |
     +---- MCP client (stdio)
               |
               v
          MCP server: app.mcp_server
               |
               v
          search_logs tool
               |
               v
          app/logs_data.py (sample log records)
```

MCP is the tool interface in this project. It allows the agent application to discover and invoke a separately defined tool rather than importing and calling the log-search function directly.

## 3. Project structure

The files verified in the repository are:

```text
grounded_agent/
├── README.md
└── app/
    ├── main.py              # FastAPI endpoint, Ollama agent loop, local/MCP tool dispatch
    ├── tools.py             # Payment health check and mock order lookup
    ├── logs_data.py         # Sample application logs (no database)
    ├── mcp_server.py        # MCP server and search_logs tool
    └── test_mcp_client.py   # Manual MCP client smoke test
```

## 4. Prerequisites

- Python 3.12 (the project has been exercised in a Python 3.12 virtual environment).
- Ollama installed and running locally.
- The Ollama model `llama3.2:3b` downloaded.
- A terminal and curl for API smoke tests.

No PostgreSQL, MySQL, or other database is required for the current implementation.

## 5. Installation on macOS

Run commands from the cloned repository root.

### 5.1 Clone and create a virtual environment

```bash
git clone https://github.com/adm-l/grounded_agent.git
cd grounded_agent

python3.12 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
```

If the repository is already cloned and the virtual environment exists, enter the project directory and activate it instead of recreating it.

### 5.2 Install Python dependencies

The current application imports FastAPI, Pydantic, Uvicorn, the Ollama Python SDK, HTTPX, and the MCP SDK.

```bash
pip install fastapi "uvicorn[standard]" pydantic ollama httpx "mcp[cli]"
```

For repeatable installs, a pinned dependency file should be added as a follow-up task. The command above is the direct setup for the current code; it is not a pinned production lockfile.

### 5.3 Install and start Ollama

Install Ollama using the official installer for macOS if it is not already installed. Start the Ollama application/service, then pull the model:

```bash
ollama pull llama3.2:3b
ollama list
```

Ollama's local API is expected at `http://localhost:11434`. Confirm the model is available before starting the agent. The model name is currently configured in `app/main.py` as `MODEL = "llama3.2:3b"`.

## 6. Run the application

From the project root, with `.venv` activated and Ollama running:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8004 --reload
```

The local API will be available at `http://127.0.0.1:8004`. Interactive API documentation is available at `http://127.0.0.1:8004/docs`.

Check the API:

```bash
curl -s http://localhost:8004/health
```

Expected response:

```json
{"status":"ok"}
```

### Important note about the payment health tool

In the current repository, `PAYMENT_SERVICE_URL` defaults to `http://localhost:8004/health`. This checks the agent application's own health endpoint when running on port 8004; it is a **demo default**, not proof that a separate payment service is healthy. Set `PAYMENT_SERVICE_URL` to the actual service's health URL when testing against a separate service. Do not point it at an endpoint that calls back into the same tool, as that can create recursive behavior.

Example for a separate local service:

```bash
export PAYMENT_SERVICE_URL="http://localhost:9000/health"
uvicorn app.main:app --host 127.0.0.1 --port 8004 --reload
```

Only use that example if a service really is listening on port 9000.

## 7. How to use the API

### 7.1 Investigate payment-service errors

```bash
curl -s -X POST http://localhost:8004/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Find payment-service errors and explain what happened."}'
```

The sample data includes an ERROR log:

- Service: `payment-service`
- Level: `ERROR`
- Request ID: `REQ-1002`
- Message: `Payment gateway connection timed out`
- Timestamp in sample data: `2026-10-27T09:00:01`

The response includes a natural-language answer, `tool_results` showing the tool's actual output, and the number of agent iterations used. The exact wording may vary by model.

### 7.2 Look up a mock order

```bash
curl -s -X POST http://localhost:8004/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What is the status of order ORD-1001?"}'
```

The mock dataset currently includes:

| Order ID | Status | Amount |
|---|---|---:|
| `ORD-1001` | shipped | 1250 |
| `ORD-1002` | processing | 800 |

These are sample values, not live customer/order records.

### 7.3 Directly test the MCP server

This test starts an MCP server subprocess, initializes the client session, lists available tools, and calls `search_logs` directly without involving the LLM:

```bash
python -m app.test_mcp_client
```

Expected behavior: the tool is listed and the result contains one matching payment-service ERROR record, `REQ-1002`.

### 7.4 Search behavior

The MCP `search_logs` tool supports optional arguments:

- `keyword`: split into terms; every term must occur somewhere in the combined service, level, request ID, or message fields.
- `service`: case-insensitive partial match.
- `level`: case-insensitive exact match.
- `request_id`: case-insensitive exact match.

Results are limited to the first 20 matching sample records.

## 8. Configuration and implementation notes

- **LLM:** `llama3.2:3b`, configured in `app/main.py`.
- **Ollama endpoint:** `http://localhost:11434`.
- **Agent iteration cap:** `MAX_ITERATIONS = 5`.
- **MCP transport:** stdio; the FastAPI process launches `python -m app.mcp_server`.
- **Data:** in-memory Python dictionaries/lists only.
- **MCP startup requirement:** `app/mcp_server.py` must end with the startup block below. Without it, importing the module defines the tool but does not start the server when run as a module.

```python
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

- **Error handling:** agent exceptions are logged by the FastAPI application and currently returned as HTTP 502 with an error detail. For a public/production deployment, avoid exposing raw exception details to clients; return a generic error and retain diagnostic details in protected logs.
- **Debug output:** `app/main.py` currently prints selected tool names and arguments. This is useful during learning, but should be replaced by structured logging and reviewed for sensitive values before production use.

## 9. Troubleshooting

### `ModuleNotFoundError`

Activate the project virtual environment and install dependencies into that environment:

```bash
source .venv/bin/activate
python -m pip install fastapi "uvicorn[standard]" pydantic ollama httpx "mcp[cli]"
```

Check that the terminal prompt shows the active environment and that `which python` points inside `.venv`.

### Ollama connection/model errors

```bash
ollama list
curl -s http://localhost:11434/api/tags
```

Confirm Ollama is running and that `llama3.2:3b` is available.

### MCP client reports `Connection closed`

1. Inspect `app/mcp_server.py` for syntax/import errors.
2. Confirm the startup block calls `mcp.run(transport="stdio")`.
3. From the repository root and active virtual environment, run `python -m app.test_mcp_client`.
4. Do not add ordinary debug prints to stdout in the MCP server: stdout is used for the stdio protocol. Use stderr or logging configured for stderr for diagnostics.

### MCP returns zero matching logs

Run the standalone MCP client first. It bypasses Ollama and verifies the tool's filters independently. The sample log for the payment gateway timeout has service `payment-service`, level `ERROR`, and request ID `REQ-1002`. Inspect the LLM-generated tool arguments in the FastAPI terminal if the API search differs from the direct MCP test.

### HTTP 502 from `/chat`

Read the Uvicorn terminal logs for the underlying exception. The endpoint uses 502 for errors during agent execution, which can include Ollama or MCP startup/communication failures.

## 10. What we implemented, step by step

1. **Created the FastAPI entry point.** Added `GET /health` and the `POST /chat` request model.
2. **Connected the local model.** Used the Ollama Python SDK with `llama3.2:3b`.
3. **Added local tools.** Implemented a configured HTTP health check and mock order lookup.
4. **Implemented an agent loop.** Passed tool schemas to the model, dispatched requested calls, appended tool results to the conversation, and capped execution at five iterations.
5. **Created sample log data.** Added INFO, WARN, and ERROR records for payment and order services.
6. **Exposed log search through MCP.** Created the FastMCP server and its `search_logs` tool with optional filters.
7. **Added a standalone MCP smoke test.** The client initializes a session, discovers the tool, and verifies a filtered search.
8. **Connected MCP to the agent.** The FastAPI agent discovers the MCP tool schema and calls it through the MCP session.
9. **Debugged the integration.** Identified that the MCP startup block had been omitted during edits; restoring `mcp.run(transport="stdio")` fixed the client handshake.
10. **Verified end-to-end behavior.** The API returned the timeout log and an explanation based on the tool result.

## 11. Plan for the next working session

The project is a working learning prototype, not yet production-ready. A sensible next session is:

### Step 1 — Add automated tests
- Add pytest and use FastAPI's test client.
- Test `GET /health`.
- Test mock order lookup for a known and unknown order.
- Test MCP log search for service/level, keyword, request ID, and no-match cases.
- Keep tests deterministic; avoid requiring a live LLM for every unit test.

### Step 2 — Separate unit and integration tests
- Unit-test the tool functions and search filters directly.
- Keep one explicit MCP client integration test.
- Keep the Ollama-backed `POST /chat` test optional or mark it as an integration test, since it requires a running local model.

### Step 3 — Improve agent reliability
- Inspect and validate tool arguments before execution.
- Improve tool descriptions and system instructions so the model prefers structured filters where possible.
- Ensure tool results are returned to the model in the format expected by the installed Ollama SDK.
- Add a clear response when the iteration cap is reached.

### Step 4 — Clean up diagnostics and configuration
- Replace the temporary debug `print` with logging.
- Keep detailed exceptions in server logs and return generic errors to API clients.
- Add a dependency file with compatible/pinned versions.
- Make the payment service URL configurable through environment variables and document the demo default clearly.

### Step 5 — Add operational safeguards
- Add request timeout handling, input length limits, and a clear policy for which tools may be called.
- Add structured logs and request/correlation IDs.
- Add tests for malformed input and tool failures.

After those steps pass locally, consider Docker Compose, a small CI workflow, and further deployment hardening. Do not add a database unless a future feature actually needs persistent data.

## 12. Security and scope

This project is for local learning and uses synthetic data. Before exposing it beyond localhost:

- Add authentication and authorization.
- Apply request size/rate limits and timeouts.
- Restrict network destinations for any HTTP tools to prevent SSRF.
- Do not allow the model to execute arbitrary shell commands or unrestricted code.
- Treat model output and tool arguments as untrusted input.
- Redact credentials and sensitive data from logs.
- Review exception responses and disable development reload mode.
- Run the API behind an appropriately configured production server.

## 13. Useful links

- Repository: https://github.com/adm-l/grounded_agent
- FastAPI: https://fastapi.tiangolo.com/
- Ollama: https://ollama.com/
- Ollama Python library: https://github.com/ollama/ollama-python
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
