# Testing the Grounded Agent

This repository uses pytest for deterministic regression tests. The core test suite does not call Ollama and does not need a running FastAPI server or a database.

## Setup

From the repository root, activate your virtual environment and install the project dependencies:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Run the automated tests

```bash
python -m pytest -q
```

The current suite covers:

- `GET /health` returns HTTP 200 and `{"status": "ok"}`.
- Known order lookup and case-insensitive order IDs.
- Unknown order lookup.
- MCP log-search filtering by service and severity.
- MCP log-search filtering by request ID.
- Keyword search where every supplied term must match.
- Empty results for filters that match no sample logs.
- Mocked `/chat` flow: MCP tool discovery and execution, unknown tool handling, and iteration-limit behavior.\n- Tool argument validation for missing required fields and incorrect types.\n- Rejection of empty and oversized questions.\n- Generic client-facing error responses when internal exceptions occur.

## Manual MCP integration smoke test

The mocked agent-flow tests verify the orchestration logic without starting Ollama or a real MCP subprocess. The automated core tests call the log-search function directly. To verify actual MCP protocol startup, tool discovery, and a tool call through stdio, run:

```bash
python -m app.test_mcp_client
```

This test exercises the MCP client/server boundary without involving the LLM.

## Optional Ollama end-to-end check

Start Ollama and ensure `llama3.2:3b` is available, then start the API in a separate terminal:

```bash
ollama pull llama3.2:3b
uvicorn app.main:app --host 127.0.0.1 --port 8004
```

In another terminal:

```bash
curl -s -X POST http://localhost:8004/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Find payment-service errors and explain what happened."}'
```

This is a manual integration check because it depends on a running local model and can produce model-dependent wording. The deterministic pytest suite deliberately avoids requiring Ollama for every test.

## Configuration and safety behavior\n\nThe agent reads these optional environment variables:\n\n- `OLLAMA_HOST` (default `http://localhost:11434`)\n- `OLLAMA_MODEL` (default `llama3.2:3b`)\n- `OLLAMA_TIMEOUT_SECONDS` (default `30`)\n- `MCP_TIMEOUT_SECONDS` (default `10`)\n- `AGENT_MAX_ITERATIONS` (default `5`)\n- `LOG_LEVEL` (default `INFO`)\n\nThe API limits questions to 4,000 characters, adds or propagates an `X-Request-ID`, validates basic tool argument types, and avoids returning raw exception messages to clients. The JSON Schema validation is deliberately limited and should not be treated as a full schema validator.\n\n## Current limitations

- These tests use synthetic in-memory data.
- The `/chat` tests use fake Ollama responses and a fake MCP session; they do not prove compatibility with every installed Ollama/MCP SDK version.
- The real MCP protocol smoke test is manual, not part of the default pytest run.
- Tests have been committed but not executed in this environment; run them locally in the project virtual environment to confirm compatibility with your installed dependency versions. Timeouts and mocked failure cases also need to be exercised in the target environment.
