# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This project is in the **design/planning phase**. The `docs/` directory contains detailed specifications, but implementation has not begun. There is no source code, no build system, and no tests yet.

## Project Overview

An AI-powered SQL debugging tool with a hybrid local+cloud architecture:

- **Local backend** (Python/FastAPI, runs on user's machine): holds DB credentials, executes queries, enforces table access rules, caps result sizes
- **Cloud backend** (Python/FastAPI, hosted on Railway/Render): runs LLM/agent reasoning — never sees credentials or query results
- **Frontend**: loaded from cloud, runs in browser, talks to both backends independently

The key security invariant: credentials and query results never leave the local machine. The cloud only receives query text for AI reasoning.

## Architecture

```
Browser (frontend JS)
  ├── localhost:8765  (Local Backend — credentials, query execution)
  └── api.yourapp.com (Cloud Backend — LLM/agent analysis)
        |
      User's DB (Postgres, MySQL, BigQuery, Snowflake)
```

### Planned Local Backend Structure

```
local_backend/
├── main.py                    # FastAPI app + startup reconciliation
├── api/connections.py         # Route handlers
├── models/                    # Pydantic models (connection, tables, common)
├── services/connection_service.py
├── db/                        # Abstract DatabaseAdapter + per-DB implementations
├── storage/config_store.py    # config.json + OS keyring
└── errors/exceptions.py
```

**Storage model:** `~/.sql-debugger/config.json` for metadata, OS keyring for passwords (encrypted file fallback).

### Tech Stack

| Layer | Choice |
|-------|--------|
| Local + Cloud backends | Python, FastAPI |
| SQL parsing | sqlglot (dialect-agnostic) |
| Credentials | OS keyring + encrypted file fallback |
| Agent framework | LangChain or similar |
| LLM | Claude/GPT-4 (controlled by us, no BYO key in MVP) |
| DB libraries | psycopg2, mysql-connector, google-cloud-bigquery, snowflake-connector |
| Deployment | Docker + docker-compose |

## Key Specifications

- **`docs/project-overview.md`** — Product vision, architecture diagrams, feature matrix, agentic debugging scope, deployment strategy
- **`docs/01-connection-management-frontend.md`** — 6 UI components, 12 API endpoints with full request/response specs, 30 UI tests
- **`docs/02-connection-management-backend.md`** — Backend structure, storage format, 96 planned tests, startup reconciliation logic

## MVP Scope

**In:** Connection management, schema browser, query console, CTE/subquery lineage visualization, click-to-execute any lineage node, filter/ORDER BY injection, results viewer, agentic debugging ("why is X null?"), free chat

**Out:** Query optimization, cross-query/pipeline debugging, column-level lineage, pagination, BYO API key, desktop executable

## Agentic Debugging Behavior

Agent scope is limited to **within a single query**. It can parse lineage, execute partial queries, and identify root causes (e.g., why a JOIN produces NULLs). It cannot trace across multiple queries or pipelines.

Free chat guardrails block general SQL tutoring, DDL/DML operations (DROP, DELETE, UPDATE, INSERT), and unrelated questions.

## Development Setup (When Implementation Begins)

- Python 3.14, virtual environment at `.venv/`
- Planned install: `pip install sql-debugger` → `sql-debugger start --port 8765`
- Database adapters will require Docker for integration tests
