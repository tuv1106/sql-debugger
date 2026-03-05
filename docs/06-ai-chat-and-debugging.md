# AI Chat & Agentic Debugging — Spec

## Document Info

| Item | Value |
|------|-------|
| Feature | AI Chat Panel, Agentic Debugging |
| Layer | Cloud Backend + Frontend |
| Status | Agreed |
| Date | March 2026 |
| Dependencies | `04-query-console-design.md`, `05-query-console-lineage-detailed.md`, `07-cloud-backend.md` |

---

## 1. Overview

The AI Assistant panel provides two modes: **Chat** (free conversation about queries, schema, SQL) and **Debug** (structured investigation of query bugs). Both run on the cloud backend, communicate with the frontend via SSE + HTTP POST, and execute queries against the user's DB through the frontend as a proxy.

### Key Principles

- **Frontend as proxy** — cloud and local backend never communicate directly. The browser mediates all query execution.
- **Two separate agents** — Chat (Q&A, no structured flow) and Debug (structured wizard, multi-step investigation).
- **Skeptical investigator** — the debug agent does not assume the user's hypothesis is correct. It investigates objectively.
- **Read-only** — both agents can only execute SELECT queries. No DDL/DML.
- **Exclusion enforcement is server-side** — the local backend enforces table exclusions. Agents never see excluded table data.

---

## 2. Architecture

### Frontend Proxy Flow

```
User clicks "Debug" or sends chat message
         │
         ▼
   Frontend → POST /debug/sessions (or /chat/sessions) → Cloud Backend
         ← { session_id: "abc-123" }
         │
   Frontend opens SSE: GET /sessions/abc-123/stream
         │
         ▼
   Agent runs on cloud, needs to execute a query:
         ← SSE event: { type: "tool_call", call_id: "t1", tool: "execute_query", ... }
         │
   Frontend receives event → forwards to Local Backend → gets results
         → POST /sessions/abc-123/respond { call_id: "t1", result: { ... } }
         │
   Cloud routes response to session abc-123, resumes agent
         │
   Agent continues → more tool calls or conclusion
         ← SSE event: { type: "conclusion", report: { ... } }
```

### Communication Protocol

| Direction | Protocol | Used for |
|-----------|----------|----------|
| Cloud → Frontend | SSE (Server-Sent Events) | Progress updates, tool call requests, follow-up questions, streamed responses |
| Frontend → Cloud | HTTP POST | Tool call results, user answers, cancel, new messages |

**Why SSE + POST (not WebSocket):**
- Works through corporate firewalls/proxies (standard HTTP)
- Auto-reconnects natively (EventSource API)
- Simpler to implement — no connection management, heartbeats, or reconnection logic
- Latency difference is negligible (~1.5s total across a session vs. WebSocket)

### Session Management

| Component | Role |
|-----------|------|
| Session store | In-memory map of `session_id → agent state` |
| SSE registry | Map of `session_id → open SSE connection` |
| `/respond` endpoint | Looks up session by ID, matches `call_id`, resumes agent |

**Multi-user isolation:**
- Each user gets a unique `session_id` (UUID)
- Sessions are fully independent — no shared mutable state
- One session crash does not affect others
- Memory per session: ~1-2MB (query text, lineage, schema, tool call results)

**Server restart:** In-memory sessions are lost. Frontend shows "Debug session lost. Please retry." Acceptable for MVP.

### Scaling

Single server for MVP. FastAPI async handles hundreds of concurrent SSE connections. The server is I/O bound (waiting for LLM API + frontend tool results).

**Post-MVP exit path:** Move session store to Redis → stateless servers behind load balancer.

---

## 3. Two Agents

| | Debug Agent | Chat Agent |
|---|-----------|-----------|
| **Purpose** | Find bugs via structured investigation | Explain, suggest, explore |
| **Entry** | Structured wizard (category → details → hint → go) | Free text |
| **Conversation** | Semi-structured (agent drives) | Free (user drives) |
| **Tools** | `validate_query`, `execute_query`, `get_schema`, `get_node_results`, `get_lineage` | `table_profile`, `get_indexes`, `sample_data` |
| **Output** | Structured report (conclusion, investigation, next steps, limitations) | Free-form responses with inline data |
| **Guardrails** | SELECT only, excluded tables blocked, query/retry limits | Same table restrictions, no DDL/DML, topic restrictions |

---

## 4. Debug Agent

### 4.1 Tools

| Tool | What it does | Via local backend? |
|------|-------------|-------------------|
| `validate_query` | Syntax check (sqlglot) + verify no excluded tables + SELECT only. Returns available columns on SELECT * rejection. | Yes |
| `execute_query` | Validates first, then executes. Rejects if validation fails. | Yes |
| `get_schema` | Table/column metadata — excluded tables omitted entirely. | Yes |
| `get_node_results` | Execute node subtree — rejects if any table in subtree is excluded. | Yes |
| `get_lineage` | Get parsed lineage graph for current query. | No (cached from parse) |

**Exclusion enforcement:** The local backend walks the node's dependency tree and checks every table source against exclusions before executing. If any excluded → error: "Cannot execute — node depends on restricted tables."

### 4.2 Debug Wizard

Entry into debug mode is structured. The user selects a bug category, provides details, and optionally gives a hint.

**Wizard steps:**

| Step | What happens |
|------|-------------|
| 1. Category | User picks: row count / nulls / values / missing columns / duplicate columns |
| 2. Details | Category-specific follow-up (see below) + free text description |
| 3. Hint (optional) | Free text: "I think the problem is in the orders CTE" |
| 4. Go | Agent starts investigation |

**Category-specific follow-ups (step 2):**

| Category | Structured options | Then |
|----------|-------------------|------|
| Unexpected row count | Too many / Too few / No results | Free text: "describe what you see" |
| Unexpected nulls | Which column(s)? (multi-select from output columns) | Free text (optional) |
| Unexpected values | Which column? + free text: "what did you expect?" | — |
| Missing columns | Free text: which column? | — |
| Duplicate columns | Free text: which column? | — |

**One bug type per session.** If the user wants to investigate a second bug, they start a new debug session after the first completes. The observation mechanism catches related issues within a single session.

**One debug session at a time.** Second attempt → "A debug session is already running. Cancel it first or wait for it to finish."

### 4.3 Investigation Behavior

The agent always starts from the **final query output** and traces backwards through the lineage. The user does not need to select a node — the agent navigates the lineage itself.

If the user has prior insight, they can:
- Truncate the query in the editor (debug only the relevant part)
- Provide a hint in the wizard ("I think the problem is in the orders CTE")

**Investigation flow:**
1. Agent receives: bug category, user description, hint, query text, lineage, schema
2. Agent plans investigation based on category (e.g., unexpected nulls → trace column lineage)
3. Agent executes investigative queries via tools
4. Agent classifies finding and produces report

**Agent is a skeptical investigator:** It does not assume the user's hypothesis is correct. If the data is valid and the user's expectation was wrong, the agent says so.

### 4.4 Verdicts

| Verdict | Meaning | Example |
|---------|---------|---------|
| **Query bug** | Query logic is wrong | LEFT JOIN should be INNER JOIN, missing WHERE clause |
| **Expected behavior** | Data is correct, user's expectation was off | Negative amounts are return transactions |
| **Potential data bug** | Data itself looks suspicious, not the query | impressions < engagements, duplicate product_id with different manufacturers |

**Potential data bug:** The agent flags data anomalies it encounters during investigation but cannot definitively confirm (it doesn't know all business rules). Reported as observations, not conclusions.

### 4.5 Report Structure

| Section | When shown | Content |
|---------|-----------|---------|
| **Conclusion** | Always | Verdict (query bug / expected behavior / potential data bug) + one-sentence summary |
| **Investigation** | Always | Ordered list of steps (see below) |
| **Next Steps** | Always | Fix suggestions (if bug) or optional filtering suggestions (if expected behavior) or further investigation suggestions |
| **Limitations** | Only if applicable | What was missing — access restrictions, timeouts, query limit reached, ambiguous data |

**Investigation steps:**
Each step contains:
- Summary line (what was checked)
- Expandable evidence: the SQL query + result table (collapsed by default)
- What was found (one line)

**When a query supports multiple steps:** Show the query on the first step. Later steps back-reference: "see step 2" with a clickable link.

**Observations:** Anomalies discovered during investigation appear as additional steps marked with ⚠. Each observation has its own evidence.

**Evidence result tables:** Fixed viewport ~5 rows × 5 columns, scrollable both axes. Does not blow up the chat layout.

### 4.6 Session Limits

| Guardrail | Limit | What happens |
|-----------|-------|-------------|
| Max queries per debug session | 15 | Agent stops, produces partial report |
| Max retries on failed/invalid query | 3 | Agent gives up on that approach, tries different angle or reports limitation |
| Max LLM calls per session | 20 | Agent wraps up with current findings |
| Query timeout | 60s (configurable) | Agent gets timeout error, can simplify query or move on |

When any limit is hit, the agent produces its report with what it found so far and explains the limitation.

### 4.7 Context Management

**Problem:** Query results can explode the LLM context window.

**Prevention (system prompt):**
- "ALWAYS specify columns. NEVER use SELECT *."
- "Use COUNT/GROUP BY to check patterns before fetching raw rows."
- "Write focused queries — SELECT only the columns you need."

**Enforcement (validation):**
- `validate_query` rejects SELECT *. Returns error with available columns so the agent can fix in one retry.
- Results capped at 50 rows in agent context. Agent sees: "Result: 1,847 rows × 8 columns. Showing first 50 rows. 1,797 rows truncated."
- Cell values truncated at 200 characters.
- No column limit — agent specifies columns explicitly.

### 4.8 Progress UI

During investigation, the panel shows a compact list of actions:

```
┌─────────────────────────────┐
│  AI Assistant   [Debug ▼] X │
│                              │
│  Debugging: Unexpected       │
│  nulls in "price"            │
│                              │
│  Checked enriched CTE for    │
│  null prices                 │
│  Looked up product_ids in    │
│  products table              │
│  Checking JOIN type...       │
│                              │
│  This may take a few minutes │
│                              │
│  [Cancel]                    │
└─────────────────────────────┘
```

- Actions appear one by one (one line per action summary)
- Current action at the bottom (text implies in-progress)
- No icons (no ✅/❌)
- Sound notification when report is ready
- If user is on a different tab, the debug tab shows a badge indicator

---

## 5. Chat Agent

### 5.1 Tools

| Tool | What it does | Via local backend? |
|------|-------------|-------------------|
| `table_profile` | Row count, column count, nulls per column, distinct counts, min/max for numerics — like `df.describe()` | Yes |
| `get_indexes` | Indexes, partitions, primary keys on a table | Yes |
| `sample_data` | Show N sample rows from any node in the lineage | Yes |

**Exclusion enforcement:**
- `table_profile` and `get_indexes` reject excluded tables
- `sample_data` rejects nodes with any excluded table in the subtree

**Tool results appear inline** in the agent's response. No "tool usage" indicator shown to the user. The agent weaves data naturally into its response.

**`table_profile` inline example:**

```
The orders table has 5,230 rows and 8 columns.

| Column     | Non-null | Distinct | Min  | Max    |
|------------|----------|----------|------|--------|
| id         | 5,230    | 5,230    | 1    | 5,230  |
| product_id | 5,198    | 342      | 1    | 500    |
| price      | 4,891    | 156      | 0.99 | 999.00 |

32 rows have null product_id. 339 rows have null price.
```

**`get_indexes` inline example:**

```
orders has 2 indexes:
- PRIMARY KEY (id)
- INDEX idx_status (status)

No partitioning configured.
```

**`sample_data`:** Small inline table, same 5×5 scrollable viewport as debug evidence.

### 5.2 Allowed Topics

| # | Topic | Example |
|---|-------|---------|
| 1 | Current query + lineage | "What does this CTE do?" "What feeds into the enriched node?" |
| 2 | Database schema | "What columns does orders have?" "What type is status?" |
| 3 | General SQL | "CTEs vs subqueries?" "What does COALESCE do?" |
| 4 | DB-specific features | "Does BigQuery support partitioning?" "Postgres index types?" |
| 5 | Domain interpretation | "What do negative amounts mean?" |

### 5.3 Blocked Topics

| Blocked | Why |
|---------|-----|
| DDL/DML generation (DROP, DELETE, UPDATE, INSERT) | Safety — agent is read-only |
| Write new queries from scratch ("write me a query that...") | Not a query generator |
| Non-SQL topics | Out of product scope |
| Cross-query/pipeline debugging | Out of MVP scope |

### 5.4 Soft Redirect to Debug

When the chat agent detects the user describing something unexpected or bug-like ("why are there nulls?", "this number seems wrong"), it suggests: **"It sounds like something is unexpected. Want to switch to Debug mode to investigate?"**

This is a suggestion, not a hard block. The chat agent can still answer domain interpretation questions ("what do negative amounts mean?").

---

## 6. Chat Panel UI

### 6.1 Panel Layout

Right sidebar, hidden by default, toggleable.

```
┌──────────────────────────────────┐
│  AI Assistant  [Chat ▼]       X  │
│  ┌────────┐ ┌────────┐ [+]      │
│  │ Chat 1 │ │ Chat 2 │          │
│  └────────┘ └────────┘          │
│                                  │
│  Context: query loaded, 5 CTEs,  │
│  schema: public (12 tables)      │
│                                  │
│  (conversation messages)         │
│                                  │
│  [Type a message...]        [→]  │
└──────────────────────────────────┘
```

### 6.2 Mode Switching

Dropdown selector (similar to Copilot's mode selector):
- **Chat** — free conversation
- **Debug** — structured wizard

Mode is **per-tab**. Each tab is either a chat or debug session, set when created.

### 6.3 Tab Management

- `[+]` button → "New Chat" / "New Debug"
- Each tab has its own conversation history and session_id
- Switching tabs preserves history for both
- Chat and debug histories are separate
- Closing a tab clears its session
- Debug tab shows badge indicator when report is ready and tab is not active

### 6.4 Context Indicator

Shown at the top of the conversation area:

```
Context: query loaded, 5 CTEs, schema: public (12 tables)
```

Helps the user understand what the agent "knows" without asking. Updates when query or connection changes.

### 6.5 Chat Mode

- Standard chat interface: user messages and streamed responses
- Scrollable conversation history
- Context indicator at top
- No tool usage visibility — agent responses include data inline naturally

### 6.6 Debug Mode — Wizard

```
┌─────────────────────────────┐
│  AI Assistant   [Debug ▼] X │
│                              │
│  What's the problem?         │
│                              │
│  ○ Unexpected row count      │
│  ○ Unexpected nulls          │
│  ○ Unexpected values         │
│  ○ Missing columns           │
│  ○ Duplicate columns         │
│                              │
│  [Next →]                    │
└─────────────────────────────┘
```

After category → follow-up questions → optional hint → investigation starts.

### 6.7 Concurrent Usage

Users can switch between chat and debug tabs freely:
- Start a debug → switch to chat tab while waiting → come back when debug finishes
- Multiple chat tabs allowed
- One debug session at a time
- SSE connections stay open for all active sessions

---

## 7. API Key & Cost Control

### API Key Security

- Stored as environment variable on Railway/Render (encrypted at rest by platform)
- Never sent to frontend or local backend
- Only the cloud backend process can read it
- Rotatable without user impact

### Cost Control

**Global budget cap:** Set a spending limit on the LLM provider account (e.g., $100 on Anthropic). When exhausted, all users get: "AI service temporarily unavailable."

**Per-session guardrails** prevent one session from burning through the budget (see Section 4.6 — session limits).

No per-user tracking or authentication in MVP. The global cap + session limits are sufficient.

---

## 8. System Prompts

### Chat Agent Prompt

| Section | Content |
|---------|---------|
| Role | "You are a SQL assistant embedded in a debugging tool. You help users understand their queries, schema, and data." |
| Context (injected per-session) | Query text, lineage graph, schema metadata, active connection DB type |
| Tools | `table_profile`, `get_indexes`, `sample_data` with usage instructions |
| Allowed topics | Query explanation, schema questions, general SQL, DB-specific features, domain interpretation |
| Blocked topics | DDL/DML generation, writing new queries from scratch, non-SQL topics, cross-query debugging |
| Soft redirect | "If the user describes something unexpected or bug-like, suggest switching to Debug mode." |
| DB dialect | "The user is connected to {db_type}. Use {db_type}-appropriate syntax and features." |

### Debug Agent Prompt

| Section | Content |
|---------|---------|
| Role | "You are a SQL debugging investigator. You trace issues through query lineage to find root causes." |
| Context (injected per-session) | Same as chat + bug category, user description, user hint, last query results summary |
| Tools | `validate_query`, `execute_query`, `get_schema`, `get_node_results`, `get_lineage` with usage instructions |
| Investigation rules | "Be skeptical — don't assume the user's hypothesis is correct. Investigate objectively. If the data is valid, say so." |
| Verdicts | "Classify as: Query Bug, Expected Behavior, or Potential Data Bug." |
| Query rules | "NEVER use SELECT *. Always specify columns. Check schema before writing queries. Use COUNT/GROUP BY before fetching raw rows." |
| Report format | Conclusion (with verdict) → Investigation steps (with evidence) → Next steps → Limitations |
| Limits | "You have a maximum of {N} queries. Be efficient." |

---

## 9. Edge Cases

| # | Edge case | How handled |
|---|-----------|------------|
| 1 | User starts debug with no query loaded | Block — "Load a query first to start debugging" |
| 2 | User starts debug with unparseable query | Block — "Fix syntax errors before debugging" |
| 3 | User edits query while debug is running | Debug continues on original query. Banner: "Query changed since debug started. Results may not match current editor." |
| 4 | User switches connection while debug is running | Cancel debug. "Connection changed — debug session cancelled." |
| 5 | All tables in query are excluded | Block — "Cannot debug — all referenced tables are restricted" |
| 6 | Some tables excluded | Agent proceeds but cannot execute nodes depending on excluded tables. Reports in Limitations. |
| 7 | Query returns 0 rows | Valid debug scenario — "No results" is a bug category. Agent traces WHERE/JOINs. |
| 8 | Agent generates invalid SQL despite validation | Counts against retry limit (max 3). After 3 → tries different approach or reports limitation. |
| 9 | Query timeout (60s) | Agent gets timeout error. Can simplify query or move on. Reports in Limitations. |
| 10 | Agent hits max query limit | Stops, produces partial report with Limitations: "Reached query limit." |
| 11 | LLM API error (rate limit, 500) | Retry once. If still fails → "Debug interrupted — AI service temporarily unavailable." |
| 12 | SSE connection drops mid-debug | Frontend auto-reconnects. Cloud sends missed events. If session expired → "Session lost, please retry." |
| 13 | User sends chat while debug runs in another tab | Works — separate sessions, separate SSE connections. |
| 14 | Second debug session attempted | Blocked — "A debug session is already running. Cancel it first or wait." |

---

## 10. Tests

### Backend Tests (Cloud)

| # | Test | Type |
|---|------|------|
| | **Session management** | |
| 1 | Create debug session returns session_id | Unit |
| 2 | Create chat session returns session_id | Unit |
| 3 | Second debug session blocked while one is running | Unit |
| 4 | Multiple chat sessions allowed concurrently | Unit |
| 5 | Session cleanup after completion | Unit |
| 6 | Session cleanup after cancel | Unit |
| 7 | Session expires after timeout (e.g., 30 min inactive) | Unit |
| | **SSE + routing** | |
| 8 | SSE stream opens for valid session_id | Integration |
| 9 | SSE stream rejects invalid session_id | Integration |
| 10 | /respond routes tool result to correct session by session_id + call_id | Integration |
| 11 | /respond with wrong call_id returns error | Integration |
| 12 | /respond with expired session returns error | Integration |
| 13 | SSE reconnect delivers missed events | Integration |
| | **Debug agent — tool validation** | |
| 14 | validate_query rejects SELECT * | Unit |
| 15 | validate_query rejects DDL (CREATE, DROP, ALTER) | Unit |
| 16 | validate_query rejects DML (INSERT, UPDATE, DELETE) | Unit |
| 17 | validate_query rejects query referencing excluded table | Unit |
| 18 | validate_query accepts valid SELECT with specific columns | Unit |
| 19 | validate_query returns available columns on SELECT * rejection | Unit |
| 20 | validate_query catches syntax errors | Unit |
| | **Debug agent — execution guardrails** | |
| 21 | execute_query validates before executing | Unit |
| 22 | get_node_results rejects node with excluded table in subtree | Unit |
| 23 | get_node_results succeeds when all tables in subtree are allowed | Unit |
| 24 | get_schema returns only non-excluded tables | Unit |
| 25 | Results capped at 50 rows in agent context | Unit |
| 26 | Cell values truncated at 200 chars | Unit |
| | **Debug agent — session limits** | |
| 27 | Agent stops after max queries reached, produces partial report | Integration |
| 28 | Agent retries invalid query up to 3 times then moves on | Integration |
| 29 | Agent stops after max LLM calls, produces partial report | Integration |
| 30 | Query timeout (60s) returns error to agent | Integration |
| | **Debug agent — verdicts** | |
| 31 | Agent classifies query bug correctly (e.g., wrong JOIN type) | Integration |
| 32 | Agent classifies expected behavior correctly (valid data, user expectation wrong) | Integration |
| 33 | Agent classifies potential data bug correctly (e.g., impressions < engagements) | Integration |
| 34 | Agent reports observations discovered during investigation | Integration |
| | **Debug agent — report structure** | |
| 35 | Report contains conclusion with verdict | Unit |
| 36 | Report contains ordered investigation steps | Unit |
| 37 | Each investigation step has summary + query + results | Unit |
| 38 | Report contains next steps (fix suggestions) | Unit |
| 39 | Report contains limitations when applicable | Unit |
| 40 | Investigation step references earlier step's evidence when query reused | Unit |
| | **Chat agent — tools** | |
| 41 | table_profile returns row count, null counts, distinct counts, min/max | Unit |
| 42 | table_profile rejects excluded table | Unit |
| 43 | get_indexes returns indexes and partitions | Unit |
| 44 | get_indexes rejects excluded table | Unit |
| 45 | sample_data returns N rows from node | Unit |
| 46 | sample_data rejects node with excluded table in subtree | Unit |
| | **Chat agent — guardrails** | |
| 47 | Chat responds to query explanation questions | Integration |
| 48 | Chat responds to general SQL questions | Integration |
| 49 | Chat responds to DB-specific feature questions | Integration |
| 50 | Chat blocks DDL/DML generation requests | Integration |
| 51 | Chat blocks "write me a query" requests | Integration |
| 52 | Chat blocks non-SQL topics | Integration |
| 53 | Chat suggests debug mode when user describes unexpected behavior | Integration |

### Frontend Tests

| # | Test | Type |
|---|------|------|
| | **Panel + mode switching** | |
| 54 | Panel hidden by default | Unit |
| 55 | Toggle button opens/closes panel | Unit |
| 56 | Mode dropdown switches between Chat and Debug | Unit |
| 57 | Each tab retains its own mode | Unit |
| | **Tab management** | |
| 58 | [+] button shows "New Chat" / "New Debug" options | Unit |
| 59 | New tab opens with empty conversation | Unit |
| 60 | Switching tabs preserves conversation history | Unit |
| 61 | Closing tab clears its session | Unit |
| 62 | Debug tab shows badge when report ready and tab not active | Unit |
| | **Chat mode** | |
| 63 | Context indicator shows query status, CTE count, schema summary | Unit |
| 64 | User message sent and streamed response displayed | Integration |
| 65 | Chat history scrollable | Unit |
| 66 | New chat starts with empty history | Unit |
| | **Debug wizard** | |
| 67 | Category selection screen shows all 5 categories | Unit |
| 68 | Sub-options shown after category selection | Unit |
| 69 | Free text description field shown after sub-option | Unit |
| 70 | Hint field optional, can be skipped | Unit |
| 71 | "Go" button starts investigation | Unit |
| 72 | Wizard blocked when no query loaded — shows message | Unit |
| 73 | Wizard blocked when query has syntax errors — shows message | Unit |
| | **Debug progress** | |
| 74 | Action summaries appear one by one during investigation | Unit |
| 75 | "This may take a few minutes" shown | Unit |
| 76 | Cancel button stops debug session | Integration |
| 77 | Sound notification on completion | Unit |
| | **Debug report** | |
| 78 | Conclusion shows verdict (query bug / expected / potential data bug) | Unit |
| 79 | Investigation steps shown in order | Unit |
| 80 | Each step has expandable evidence (query + results) | Unit |
| 81 | Evidence table is 5x5 fixed viewport, scrollable | Unit |
| 82 | Back-reference ("see step 2") links to correct step | Unit |
| 83 | Observations marked with warning indicator | Unit |
| 84 | Next steps section shown | Unit |
| 85 | Limitations section shown when applicable | Unit |
| | **Connection switch** | |
| 86 | Connection switch cancels active debug session | Integration |
| 87 | Connection switch shows cancellation message | Unit |
| 88 | Chat sessions cleared on connection switch | Integration |
| | **Edge cases** | |
| 89 | Second debug session blocked — shows message | Unit |
| 90 | Query edited during debug — banner shown | Unit |
| 91 | All tables excluded — debug blocked with message | Unit |
| 92 | SSE disconnect — auto-reconnect | Integration |
| 93 | LLM API error — retry once then show error | Integration |

### Summary: 93 tests (53 backend + 40 frontend)

---

## 11. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent framework | LangGraph (LangChain ecosystem) | Structured agent flows, good Claude support via ChatAnthropic, active community. See `07-cloud-backend.md` for full cloud backend spec. |
| Agent architecture | Frontend as proxy (browser mediates cloud ↔ local) | Maintains clean architecture — local backend never talks to cloud. No tunnel infrastructure needed. |
| Two agents | Separate chat and debug agents | Different behaviors: chat is stateless Q&A, debug is multi-step tool-using investigation. Simpler prompts, clearer guardrails, easier eval. |
| Communication protocol | SSE + HTTP POST (not WebSocket) | Works through corporate firewalls, auto-reconnects, simpler implementation. Latency difference negligible. |
| Debug entry | Structured wizard (category → details → hint) | Focused investigation, fewer wasted queries, easier eval per category. |
| One bug per session | Single bug type per debug session | Keeps agent focused, avoids hitting query limits. Observations catch related issues. |
| One debug at a time | Second debug blocked | Cost control, avoids confusion. |
| Verdicts | Three: query bug, expected behavior, potential data bug | Agent is a skeptical investigator, not a yes-man. Reports data anomalies it encounters. |
| Report structure | Conclusion → Investigation (expandable evidence) → Next steps → Limitations | Evidence co-located with each step, no cross-referencing needed. |
| Shared query evidence | Show on first step, later steps back-reference | Avoids duplication, keeps report clean. |
| SELECT * blocked | Validation rejects + system prompt instructs | Prevents context explosion. Agent has schema, no excuse for SELECT *. |
| Result cap | 50 rows in agent context, 200 char cell limit | Hard safety net. Agent should write focused queries anyway. |
| API key | Cloud backend env var, global budget cap at provider | Simple for MVP. No per-user auth needed. |
| Session limits | 15 queries, 3 retries, 20 LLM calls per session | Prevents runaway sessions from burning budget. |
| Chat tools | table_profile, get_indexes, sample_data | Gives chat agent unique value over plain LLM (live DB access). Without these, users would just paste query into Gemini. |
| Tool visibility in chat | Hidden — results inline in response | Cleaner UX. User doesn't need to know a tool was called. |
| Allowed SQL topics | Broad — general SQL allowed for MVP | Hard to enforce "is this related to your query." Tighten post-MVP if needed. |
| Soft redirect to debug | Chat suggests debug mode when user describes unexpected behavior | Avoids hard line between interpretation and debugging. |
| Tab management | Per-tab mode, multiple chat tabs, one debug at a time | Users can chat while debug runs. Badge notification when done. |
| Context indicator | Show what agent knows (query status, CTE count, schema summary) | Helps user understand agent's context without asking. |
| User notification | Sound + badge when debug complete | Debug takes minutes — user may be working elsewhere. |
| Server scaling | Single server for MVP | I/O bound, FastAPI async handles hundreds of connections. Redis exit path for post-MVP. |
| Session isolation | In-memory, per session_id, no shared mutable state | Each session ~1-2MB. 50 concurrent users = ~100MB. Crash isolation. |

---

## 12. Related Documents

- `04-query-console-design.md` — Overall application layout, Query Console
- `05-query-console-lineage-detailed.md` — Lineage visualization, node execution, results viewer
- `07-cloud-backend.md` — Cloud backend spec (endpoints, session management, LangGraph agents)
- `02-connection-management-backend-v2.md` — Entity exclusion model, local backend endpoints
- `project-overview.md` — MVP scope, agentic debugging overview

---

*End of AI Chat & Agentic Debugging Spec*