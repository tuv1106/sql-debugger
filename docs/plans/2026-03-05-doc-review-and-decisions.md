# Doc Review & Design Decisions — March 2026

## Summary

Review of all 7 spec documents for consistency, gaps, and missing specs. Resulted in fixes, new decisions, and one new spec document.

## Inconsistencies Fixed

1. **Node ID format** — removed type prefixes (`cte_orders` → `orders`). Fixed in docs 04, 05.
2. **Injection method** — doc 04 described subquery wrapping, doc 05 uses AST manipulation (correct). Fixed doc 04.
3. **Schema Browser default** — doc 04 said "Visible", doc 03 said "Hidden". Fixed doc 04 to "Hidden, toggleable".
4. **Endpoint naming** — `/query/preview` → `/query/effective-sql`. Fixed doc 04.
5. **File references** — wrong filenames in docs 02, 03, 04. Fixed.

## Design Decisions Made

### Frontend Tech Stack
- React 19 + TypeScript + Vite
- Tailwind CSS (styling)
- Zustand (state management)
- CodeMirror 6 (SQL editor)
- React Flow + ELK (lineage graph)
- TanStack Table (results viewer)

### Agent Framework
- LangGraph (LangChain ecosystem) with ChatAnthropic for Claude

### Snowflake
- Deferred to post-MVP. Focus on Postgres, MySQL, BigQuery.

### Connection Switch
- Full reset: cancel all in-flight ops, clear lineage/results/injections/chat/debug sessions.

### AI Tool Endpoints
- 8 cloud-side agent tools mapping to local backend endpoints
- 3 new local backend endpoints: `/tables/{table}/profile`, `/tables/{table}/indexes`, `/sample`
- Existing endpoints get exclusion enforcement and SELECT-only checks

### BigQuery Service Account JSON
- Paste or file-pick in frontend → arrives as JSON string in request body → stored in keyring

## New Document
- `07-cloud-backend.md` — full cloud backend spec (endpoints, sessions, LangGraph agents, tool mapping)

## Documents Updated
- `project-overview.md` — tech stack, connection switch rule, feature spec table
- `01-connection-management-frontend-v2.md` — Snowflake post-MVP
- `02-connection-management-backend-v2.md` — Snowflake post-MVP, 3 new endpoints, file refs
- `03-schema-browser-frontend.md` — Snowflake post-MVP, file refs
- `04-query-console-design.md` — node IDs, injection method, schema browser default, endpoint name, file refs
- `05-query-console-lineage-detailed.md` — node IDs
- `06-ai-chat-and-debugging.md` — LangGraph, cross-refs to doc 07
