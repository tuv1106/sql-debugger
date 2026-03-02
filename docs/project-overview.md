# SQL Debugger — Project Overview

**Version:** 1.0  
**Date:** February 2026  
**Status:** MVP Planning

---

## Product Vision

An AI-powered SQL debugging tool for analysts and data engineers. Combines query visualization, interactive execution, and agentic root-cause analysis to help users find bugs in complex queries.

### Target Users

- Analysts
- Data engineers

### Differentiator

Nobody offers visual lineage + click-to-execute + AI-driven debugging in one tool.

**Competitors analyzed:**
- T-SQL Debuggers (dbForge, Aqua Data Studio) — stored procedures only, not SELECT queries
- SQL Lineage/Viz (FlowHigh, SQLFlow) — visualization only, no execution
- Data Observability (Monte Carlo, Anomalo) — pipeline level, not query level
- AI SQL Assistants (BlazeSQL, Vanna.ai) — generate queries, don't debug them

---

## Architecture

### Hybrid Model

```
┌─────────────────────────────────────────────────────────────┐
│                         BROWSER                             │
│   UI JavaScript (loaded from cloud, runs locally)          │
│         │                              │                    │
│         ▼                              ▼                    │
│   localhost:8765                  api.yourapp.com           │
│   (Local Backend)                 (Cloud Backend)           │
└─────────┼──────────────────────────────┼────────────────────┘
          │                              │
          ▼                              ▼
   ┌──────────────┐              ┌──────────────┐
   │Local Backend │              │Cloud Backend │
   │ (user's PC)  │              │  (Railway)   │
   │              │              │              │
   │ - DB creds   │              │ - LLM/Agent  │
   │ - Query exec │              │ - No DB data │
   │ - Results    │              │ - Query text │
   └──────┬───────┘              └──────────────┘
          │
          ▼
   ┌──────────────┐
   │   User's DB  │
   └──────────────┘
```

### Key Security Properties

- Credentials stored in OS keyring (local only)
- Query results never touch cloud
- Cloud only sees query text for agent reasoning
- No auth needed between local and cloud (they don't communicate directly)

### Terminology

| Term | Meaning |
|------|---------|
| Local Backend | Python server on user's machine, handles DB operations |
| Cloud Backend | Railway/Render server, handles LLM/analysis |
| Agent | AI agent for debugging (uses LLM) |

---

## Database Support

| Database | MVP | Notes |
|----------|-----|-------|
| Postgres | ✅ | Primary for testing |
| MySQL | ✅ | |
| BigQuery | ✅ | Key for analytics users |
| Snowflake | ✅ | Key for analytics users |

**Parser:** sqlglot (dialect-agnostic)

---

## MVP Features

### Included

| Feature | Description |
|---------|-------------|
| Connection Management | Multiple connections, table allow/block, OS keyring storage |
| Schema Browser | Simple tree view (tables → columns) |
| Query Console | Paste, upload .sql, edit, run full query |
| Query Lineage Visualization | CTE/subquery dependency graph, click nodes |
| Click Node → Execute | Run any node, results capped |
| Filter & Order Injection | User adds WHERE/ORDER BY to any node |
| Results Viewer | Table with client-side sort/filter |
| Agentic Debugging | "Why is X null?" → trace within query, explain |
| Free Chat | Query-aware, can reference selected node |

### Excluded from MVP

| Feature | Reason |
|---------|--------|
| Query Optimization Suggestions | Separate feature, adds scope |
| Cross-query Debugging | Requires pipeline tracking |
| Column-level Lineage | Complex, not needed for core debugging |
| Aggregation Views / Data Profiling | Nice-to-have, not core |
| Pagination | Filter/order injection solves this |
| BYO API Key | Need controlled model for validation |
| Desktop exe | pip install is enough for target users |

---

## Agentic Debugging — Scope

### In Scope (Within Query)

User query:
```sql
WITH orders AS (
  SELECT * FROM raw_orders WHERE status = 'complete'
),
enriched AS (
  SELECT o.*, p.price 
  FROM orders o
  LEFT JOIN products p ON o.product_id = p.product_id
)
SELECT * FROM enriched
```

User asks: "Why is price null in row with order_id = 123?"

Agent:
1. Parses lineage: `price` comes from `products` via LEFT JOIN
2. Runs: `SELECT * FROM products WHERE product_id = (SELECT product_id FROM raw_orders WHERE order_id = 123)`
3. Finds: no matching row
4. Explains: "price is null because order 123 has product_id = 456, which doesn't exist in products table"

### Out of Scope (Cross-Query)

User asks: "Why is product 456 missing from products table?"

This requires tracing to a different query/pipeline that populates `products`. Out of MVP.

---

## Free Chat — Scope

### In Scope

- Questions about the loaded query
- "Why is X null?"
- "What does this CTE do?"
- "Which tables are joined here?"
- "Filter to show rows where price > 100"

### Out of Scope (Guardrails)

- General SQL tutoring
- "Write me a query that..."
- Questions unrelated to current query
- DDL/DML (DROP, DELETE, UPDATE, INSERT)

### Chat Context

Chat always has access to:
- Full query text
- Parsed lineage graph
- Currently selected node (if any)
- Current result set (if any)
- Schema metadata (tables, columns, types)

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| Local Backend | Python, FastAPI |
| Cloud Backend | Python, FastAPI |
| Agent Framework | LangChain (or similar) |
| SQL Parsing | sqlglot |
| LLM | Claude/GPT-4 (controlled by us) |
| Frontend | TBD (likely React) |
| Deployment | Railway or Render |
| Credential Storage | OS keyring with encrypted file fallback |

---

## Local Backend (pip install)

```bash
pip install sql-debugger
sql-debugger start --port 8765
```

### Responsibilities

- Hold DB credentials (in OS keyring)
- Execute queries from browser
- Enforce table allowlist/blocklist
- Cap result size before sending to browser
- Never send credentials or data to cloud

---

## Deployment

### Approach

- Docker + docker-compose from day one
- Deploy to Railway or Render initially
- No platform lock-in (standard Docker, env vars, no managed add-ons)

### Exit Paths

| Future Direction | Migration Effort |
|------------------|------------------|
| Full desktop (Electron) | Bundle web UI + local backend. Low effort. |
| Full cloud (AWS/GCP) | Same Docker image. Trivial. |
| Full open source | Publish Docker image + compose. Ready. |

---

## Hypotheses to Validate

| # | Hypothesis | How to Measure |
|---|------------|----------------|
| 1 | Users find this helpful | Qualitative feedback, usage patterns |
| 2 | Users willing to pay | Direct ask, signup intent |

**Parked:** Pricing model (need more usage data first)

---

## Feature Specs (Separate Documents)

| Feature | Document | Status |
|---------|----------|--------|
| Connection Management | `01-connection-management-frontend.md` | ✅ Complete |
| Connection Management Backend | TBD | Pending |
| Schema Browser | TBD | Pending |
| Query Console | TBD | Pending |
| Query Lineage Visualization | TBD | Pending |
| Click Node → Execute | TBD | Pending |
| Filter & Order Injection | TBD | Pending |
| Results Viewer | TBD | Pending |
| Agentic Debugging | TBD | Pending |
| Free Chat | TBD | Pending |

---

*End of Project Overview*
