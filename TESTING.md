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

## Manual MCP integration smoke test

The automated core tests call the log-search function directly. To verify MCP protocol startup, tool discovery, and a real MCP tool call through stdio, run:

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

## Current limitations

- These tests use synthetic in-memory data.
- The suite does not yet cover the full `POST /chat` tool-dispatch loop.
- The MCP protocol smoke test is manual, not part of the default pytest run.
- Tests have been added to the repository; run them locally in the project virtual environment to confirm compatibility with your installed dependency versions.
