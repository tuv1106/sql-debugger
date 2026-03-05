# Cloud Backend — Spec

## Document Info

| Item | Value |
|------|-------|
| Feature | Cloud Backend (AI Chat & Debug infrastructure) |
| Layer | Cloud Backend |
| Status | Agreed |
| Date | March 2026 |
| Dependencies | `06-ai-chat-and-debugging.md`, `02-connection-management-backend-v2.md` |

---

## 1. Overview

The cloud backend hosts the AI agents (Chat and Debug). It runs on Railway/Render, communicates with the frontend via SSE + HTTP POST, and never touches DB credentials or query results directly. The frontend acts as a proxy — the cloud sends tool call requests, the frontend forwards them to the local backend, and returns results.

### Key Principles

- **Stateless deployment target** — in-memory sessions for MVP, Redis exit path for post-MVP
- **Frontend as proxy** — cloud and local backend never communicate directly
- **LangGraph agents** — structured agent flows with tool use
- **SSE for streaming** — works through corporate firewalls, auto-reconnects

---

## 2. Project Structure

```
cloud_backend/
├── main.py                      # FastAPI app, lifespan, CORS
├── api/
│   ├── health.py                # GET /health
│   ├── chat.py                  # POST /chat/sessions, POST /chat/{id}/message
│   ├── debug.py                 # POST /debug/sessions
│   └── sessions.py              # GET /sessions/{id}/stream (SSE), POST /sessions/{id}/respond, POST /sessions/{id}/cancel
├── agents/
│   ├── chat_agent.py            # Chat agent: LangGraph graph definition + prompt
│   ├── debug_agent.py           # Debug agent: LangGraph graph definition + prompt
│   └── tools/
│       ├── validate_query.py    # Syntax check + exclusion + SELECT-only
│       ├── execute_query.py     # Validate then execute
│       ├── get_schema.py        # Schema metadata, excluded tables omitted
│       ├── get_node_results.py  # Execute node subtree, exclusion check
│       ├── get_lineage.py       # Parsed lineage graph (from cached parse)
│       ├── table_profile.py     # Row count, column stats
│       ├── get_indexes.py       # Indexes, PKs, partitioning
│       └── sample_data.py       # N sample rows from table/node
├── sessions/
│   ├── session_store.py         # In-memory session map (session_id → agent state)
│   └── sse_registry.py          # SSE connection management (session_id → open connection)
├── models/
│   ├── session.py               # SessionState, SessionType, SessionStatus
│   ├── events.py                # SSE event types (tool_call, progress, conclusion, error)
│   └── tool_calls.py            # ToolCallRequest, ToolCallResponse
└── config.py                    # LLM API key, session limits, timeouts
```

---

## 3. API Endpoints

### Endpoint Summary

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Health check |
| POST | `/chat/sessions` | Create a new chat session |
| POST | `/chat/{session_id}/message` | Send a message in a chat session |
| POST | `/debug/sessions` | Create a new debug session |
| GET | `/sessions/{session_id}/stream` | SSE stream for a session |
| POST | `/sessions/{session_id}/respond` | Return a tool call result to a session |
| POST | `/sessions/{session_id}/cancel` | Cancel a running session |

---

### `GET /health`

**Response (200):**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

---

### `POST /chat/sessions`

Create a new chat session.

**Request:**
```json
{
  "query_text": "WITH orders AS (...) SELECT * FROM enriched",
  "lineage": { "nodes": [...], "edges": [...] },
  "schema": { "public.orders": [...], "public.products": [...] },
  "db_type": "postgres",
  "excluded_tables": ["sensitive.users", "sensitive.payments"]
}
```

**Response (201):**
```json
{
  "session_id": "chat-abc-123",
  "session_type": "chat"
}
```

The frontend opens an SSE connection to `/sessions/chat-abc-123/stream` after creating the session.

---

### `POST /chat/{session_id}/message`

Send a user message in an existing chat session.

**Request:**
```json
{
  "message": "What does the enriched CTE do?"
}
```

**Response (202):**
```json
{
  "accepted": true
}
```

The agent processes the message and streams the response via SSE.

---

### `POST /debug/sessions`

Create a new debug session and start investigation.

**Request:**
```json
{
  "query_text": "WITH orders AS (...) SELECT * FROM enriched",
  "lineage": { "nodes": [...], "edges": [...] },
  "schema": { "public.orders": [...], "public.products": [...] },
  "db_type": "postgres",
  "excluded_tables": ["sensitive.users"],
  "bug_category": "unexpected_nulls",
  "bug_details": {
    "columns": ["price"],
    "description": "Some rows have null price even though products table has prices for all IDs"
  },
  "hint": "I think the problem is in the JOIN"
}
```

**Response (201):**
```json
{
  "session_id": "debug-def-456",
  "session_type": "debug"
}
```

**Error (409):**
```json
{
  "error": "A debug session is already running. Cancel it first or wait for it to finish."
}
```

---

### `GET /sessions/{session_id}/stream`

SSE stream for receiving events from the agent.

**Event types:**

#### `progress` — action summary during debug investigation
```json
{
  "type": "progress",
  "message": "Checking enriched CTE for null prices"
}
```

#### `tool_call` — agent needs the frontend to execute something via local backend
```json
{
  "type": "tool_call",
  "call_id": "tc-001",
  "tool": "execute_query",
  "arguments": {
    "sql": "SELECT product_id, price FROM public.products WHERE product_id IN (SELECT product_id FROM public.raw_orders WHERE order_id = 123)",
    "limit": 50
  }
}
```

#### `chat_response` — streamed chat response (partial text chunks)
```json
{
  "type": "chat_response",
  "chunk": "The `enriched` CTE joins orders with products using a LEFT JOIN, which means..."
}
```

#### `chat_response_end` — end of streamed response
```json
{
  "type": "chat_response_end"
}
```

#### `conclusion` — debug investigation complete
```json
{
  "type": "conclusion",
  "report": {
    "verdict": "query_bug",
    "summary": "price is null because order 123 has product_id 456, which doesn't exist in the products table. The LEFT JOIN preserves the row with null price.",
    "investigation_steps": [
      {
        "step": 1,
        "summary": "Checked enriched CTE output for null prices",
        "query": "SELECT order_id, product_id, price FROM enriched WHERE price IS NULL LIMIT 10",
        "result": { "columns": [...], "rows": [...], "total_rows": 339 },
        "finding": "339 rows have null price"
      },
      {
        "step": 2,
        "summary": "Looked up missing product_ids in products table",
        "query": "SELECT DISTINCT e.product_id FROM enriched e WHERE e.price IS NULL AND e.product_id NOT IN (SELECT product_id FROM public.products)",
        "result": { "columns": [...], "rows": [...], "total_rows": 32 },
        "finding": "32 product_ids in orders have no match in products"
      }
    ],
    "next_steps": [
      "Check why 32 product_ids are missing from the products table",
      "Consider using INNER JOIN if unmatched orders should be excluded"
    ],
    "limitations": []
  }
}
```

#### `error` — session error
```json
{
  "type": "error",
  "message": "AI service temporarily unavailable"
}
```

**SSE reconnection:** If the connection drops and the frontend reconnects, the server replays any missed events since the last received event. Events are stored per-session with sequence numbers.

---

### `POST /sessions/{session_id}/respond`

Return a tool call result from the frontend (after executing on local backend).

**Request:**
```json
{
  "call_id": "tc-001",
  "result": {
    "columns": [
      { "name": "product_id", "type": "integer" },
      { "name": "price", "type": "numeric" }
    ],
    "rows": [[456, null]],
    "total_rows": 1,
    "truncated": false
  }
}
```

**Request (tool call failed):**
```json
{
  "call_id": "tc-001",
  "error": "Connection failed. Verify credentials."
}
```

**Response (200):**
```json
{
  "accepted": true
}
```

**Error (404):** Session not found or expired.
**Error (400):** Unknown call_id for this session.

---

### `POST /sessions/{session_id}/cancel`

Cancel a running session (debug or chat).

**Response (200):**
```json
{
  "cancelled": true
}
```

Debug session: agent stops, produces partial report if possible.
Chat session: current response generation stops.

---

## 4. Session Management

### Session State

```python
class SessionState:
    session_id: str                    # UUID
    session_type: "chat" | "debug"
    status: "active" | "waiting_tool" | "completed" | "cancelled" | "error"
    created_at: datetime
    last_activity: datetime

    # Agent state
    agent_state: dict                  # LangGraph checkpoint
    conversation_history: list         # Message history

    # Context (set on creation)
    query_text: str
    lineage: dict
    schema: dict
    db_type: str
    excluded_tables: list[str]

    # Debug-specific
    bug_category: str | None
    bug_details: dict | None
    hint: str | None

    # Tracking
    query_count: int                   # Queries executed so far
    llm_call_count: int                # LLM calls so far
    pending_tool_calls: dict           # call_id → awaiting response
    event_log: list                    # All SSE events (for reconnection replay)
```

### Session Lifecycle

```
Created → Active → (Waiting for tool result ↔ Active) → Completed/Cancelled/Error
```

### Session Limits

| Setting | Value |
|---------|-------|
| Session timeout (inactive) | 30 minutes |
| Max concurrent debug sessions per user | 1 |
| Max concurrent chat sessions per user | No limit |
| Max queries per debug session | 15 |
| Max retries on failed query | 3 |
| Max LLM calls per debug session | 20 |
| Query timeout | 60s |

### Session Cleanup

- Sessions are removed from memory when completed, cancelled, or expired
- A background task checks for expired sessions every 5 minutes
- On server restart: all sessions are lost. Frontend shows "Session lost. Please retry."

---

## 5. Agent Tool Mapping

Each cloud-side agent tool maps to one or more local backend endpoints via the frontend proxy.

### Debug Agent Tools

| Tool | Local Backend Endpoint | Cloud-side Logic |
|------|----------------------|-----------------|
| `validate_query` | `POST /query/parse` | Parse query, check for excluded tables in parsed nodes, verify statement is SELECT-only. No new endpoint needed. |
| `execute_query` | `POST /connections/{id}/execute` | Calls validate_query first. If valid, sends execute request via frontend proxy. Results capped at 50 rows for agent context. |
| `get_schema` | `GET /connections/{id}/entities?include_columns=true` | Filters response to remove excluded tables before passing to LLM. |
| `get_node_results` | `POST /connections/{id}/execute-node` | Checks that no table in the node's subtree is excluded. Sends execute-node request via frontend proxy. |
| `get_lineage` | (cached from session context) | Returns lineage graph from session state. No endpoint call needed. |

### Chat Agent Tools

| Tool | Local Backend Endpoint | Cloud-side Logic |
|------|----------------------|-----------------|
| `table_profile` | `GET /connections/{id}/tables/{table}/profile` | Rejects excluded tables before calling. Formats result as readable text for LLM. |
| `get_indexes` | `GET /connections/{id}/tables/{table}/indexes` | Rejects excluded tables before calling. Formats as readable text. |
| `sample_data` | `POST /connections/{id}/sample` | Rejects if table is excluded. Caps at 10 rows for context. |

### Tool Call Flow

```
1. LangGraph agent decides to call a tool
2. Cloud backend emits SSE event: { type: "tool_call", call_id, tool, arguments }
3. Frontend receives event
4. Frontend calls local backend endpoint with the arguments
5. Frontend sends result back: POST /sessions/{id}/respond { call_id, result }
6. Cloud backend routes result to the waiting agent
7. Agent continues processing
```

---

## 6. LangGraph Agent Design

### Chat Agent Graph

```
Start → Generate Response (with tools) → Stream to frontend → Wait for next message
                    ↓ (tool needed)
              Tool Call → Wait for result → Resume generation
```

Simple loop. LangGraph's `create_react_agent` handles this with tool nodes.

### Debug Agent Graph

```
Start → Plan Investigation
           ↓
        Execute Step → Tool Call → Wait for result
           ↓
        Analyze Result → (more steps needed?) → Execute Step
           ↓ (done)
        Classify Verdict → Generate Report → Stream conclusion
```

More structured. LangGraph's state machine models this as:
- `plan` node: decides next investigation step
- `execute` node: calls tools
- `analyze` node: interprets results, decides if more investigation needed
- `report` node: generates final report with verdict

### Agent Context Management

Context passed to the LLM on each call:
- System prompt (role, rules, tools, limits)
- Query text + lineage + schema (from session state)
- Bug category + details + hint (debug only)
- Conversation history (previous tool calls + results)

**Context budget:** Tool results are summarized before adding to history to prevent context overflow. Raw results are stored in session state for the report but not re-sent to the LLM on every call.

---

## 7. Tech Stack

| Component | Library |
|-----------|---------|
| Framework | FastAPI |
| Agent | LangGraph |
| LLM Client | ChatAnthropic (langchain-anthropic) |
| SSE | sse-starlette |
| Validation | Pydantic |
| Testing | pytest |
| Deployment | Docker → Railway/Render |

---

## 8. Configuration

Environment variables on Railway/Render:

| Variable | Purpose |
|----------|---------|
| `ANTHROPIC_API_KEY` | LLM API key (encrypted at rest by platform) |
| `LLM_MODEL` | Model ID (default: claude-sonnet-4-20250514) |
| `SESSION_TIMEOUT_MINUTES` | Session inactivity timeout (default: 30) |
| `MAX_QUERIES_PER_DEBUG` | Max queries per debug session (default: 15) |
| `MAX_LLM_CALLS_PER_DEBUG` | Max LLM calls per debug session (default: 20) |
| `ALLOWED_ORIGINS` | CORS allowed origins (frontend URL) |
| `LOG_LEVEL` | Logging level (default: INFO) |

---

## 9. Tests

### Unit Tests

| # | Test | Type |
|---|------|------|
| | **Session management** | |
| 1 | Create chat session returns session_id | Unit |
| 2 | Create debug session returns session_id | Unit |
| 3 | Second debug session blocked while one is running | Unit |
| 4 | Multiple chat sessions allowed concurrently | Unit |
| 5 | Session cleanup after completion | Unit |
| 6 | Session cleanup after cancel | Unit |
| 7 | Session expires after timeout | Unit |
| 8 | Session state tracks query count | Unit |
| 9 | Session state tracks LLM call count | Unit |
| | **SSE + routing** | |
| 10 | SSE stream opens for valid session_id | Integration |
| 11 | SSE stream rejects invalid session_id | Integration |
| 12 | /respond routes result to correct session by call_id | Integration |
| 13 | /respond with wrong call_id returns 400 | Integration |
| 14 | /respond with expired session returns 404 | Integration |
| 15 | SSE reconnect replays missed events | Integration |
| | **Tool mapping** | |
| 16 | validate_query rejects SELECT * | Unit |
| 17 | validate_query rejects DDL/DML | Unit |
| 18 | validate_query rejects query with excluded table | Unit |
| 19 | validate_query accepts valid SELECT | Unit |
| 20 | execute_query validates before executing | Unit |
| 21 | get_schema filters out excluded tables | Unit |
| 22 | get_node_results rejects node with excluded table in subtree | Unit |
| 23 | table_profile rejects excluded table | Unit |
| 24 | get_indexes rejects excluded table | Unit |
| 25 | sample_data rejects excluded table | Unit |
| 26 | Results capped at 50 rows for agent context | Unit |
| 27 | Cell values truncated at 200 chars | Unit |
| | **Debug agent limits** | |
| 28 | Agent stops after max queries, produces partial report | Integration |
| 29 | Agent retries invalid query up to 3 times | Integration |
| 30 | Agent stops after max LLM calls, produces partial report | Integration |
| | **Cancel** | |
| 31 | Cancel debug session stops agent | Integration |
| 32 | Cancel chat session stops response generation | Integration |
| 33 | Cancel returns partial report if possible | Integration |

### Summary: 33 tests

---

## 10. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Session storage | In-memory for MVP | Simple. Redis exit path for post-MVP scaling. |
| Agent framework | LangGraph | Structured agent flows, good Claude support, active community |
| Communication | SSE + HTTP POST | Works through firewalls, auto-reconnects, simpler than WebSocket |
| Tool execution | Frontend as proxy | Clean architecture — local and cloud never communicate directly |
| Tool result handling | Summarize before adding to LLM history | Prevents context overflow from large query results |
| SSE reconnection | Server-side event log with replay | Handles dropped connections gracefully |
| Session limits | Per-session caps (queries, LLM calls, timeout) | Prevents runaway sessions from burning LLM budget |
| One debug at a time | Blocked at session creation | Cost control, avoids user confusion |
| Context on creation | Frontend sends query + lineage + schema + exclusions | Cloud never calls local backend — has everything it needs upfront |

---

## 11. Related Documents

- `06-ai-chat-and-debugging.md` — Agent behavior, prompts, verdicts, UI
- `02-connection-management-backend-v2.md` — Local backend endpoints (including AI tool support endpoints)
- `05-query-console-lineage-detailed.md` — Parse, execute, execute-node endpoints
- `project-overview.md` — Architecture, tech stack

---

*End of Cloud Backend Spec*
