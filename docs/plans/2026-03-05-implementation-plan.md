# SQL Debugger — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an AI-powered SQL debugging tool with local+cloud architecture, supporting Postgres, MySQL, and BigQuery.

**Architecture:** Hybrid local+cloud. Local backend (Python/FastAPI) on user's machine handles DB credentials and query execution. Cloud backend (Python/FastAPI + LangGraph) handles AI reasoning. Frontend (React) loaded from cloud, runs in browser, talks to both backends. Credentials and query results never leave local machine.

**Tech Stack:**
- Local Backend: Python 3.14, FastAPI, sqlglot, psycopg2, mysql-connector, google-cloud-bigquery, keyring, pytest
- Cloud Backend: Python 3.14, FastAPI, LangGraph, langchain-anthropic, sse-starlette, pytest
- Frontend: React 19, TypeScript, Vite, Tailwind CSS, Zustand, CodeMirror 6, React Flow + ELK, TanStack Table

**Spec Documents:**
- `docs/project-overview.md` — Architecture, MVP scope, tech stack
- `docs/01-connection-management-frontend-v2.md` — Connection UI: 6 components, 14 endpoints, 36 tests
- `docs/02-connection-management-backend-v2.md` — Connection backend: models, storage, exclusions, 132 tests
- `docs/03-schema-browser-frontend.md` — Schema browser: tree, cache, 45 tests
- `docs/04-query-console-design.md` — Query console high-level design
- `docs/05-query-console-lineage-detailed.md` — Lineage, execution, results: 5 endpoints, 132 tests
- `docs/06-ai-chat-and-debugging.md` — AI chat + debug agents: 93 tests
- `docs/07-cloud-backend.md` — Cloud backend: sessions, SSE, LangGraph agents, 33 tests

---

## Dependency Graph

```
Phase 1: Scaffolding
    ↓
Phase 2: Local Backend — Connection Management
    ↓                    ↘
Phase 3: Frontend —       Phase 4: Local Backend —
  Connection Mgmt           Schema & Query Endpoints
    ↓                    ↙
Phase 5: Frontend — Schema Browser
    ↓
Phase 6: Frontend — Query Console (Editor)
    ↓
Phase 7: Frontend — Lineage Visualization
    ↓
Phase 8: Frontend — Results Viewer & Injection
    ↓                    ↘
Phase 9: Local Backend —  Phase 10: Cloud Backend
  AI Support Endpoints       (Sessions, SSE, LangGraph)
    ↓                    ↙
Phase 11: Frontend — AI Chat & Debug
    ↓
Phase 12: Integration & Polish
```

Phases 2 and 4 can run in parallel after Phase 1.
Phases 9 and 10 can run in parallel after Phase 8.

---

## Phase 1: Project Scaffolding

### Task 1.1: Local Backend Project Setup

**Files:**
- Create: `local_backend/main.py`
- Create: `local_backend/requirements.txt`
- Create: `local_backend/pyproject.toml`
- Create: `local_backend/__init__.py`
- Create: `local_backend/api/__init__.py`
- Create: `local_backend/models/__init__.py`
- Create: `local_backend/services/__init__.py`
- Create: `local_backend/db/__init__.py`
- Create: `local_backend/storage/__init__.py`
- Create: `local_backend/errors/__init__.py`
- Create: `tests/local_backend/__init__.py`
- Create: `tests/local_backend/conftest.py`
- Create: `Dockerfile.local`

**What to implement:**
- FastAPI app with CORS middleware, health endpoint (`GET /health`)
- Project structure matching `docs/02-connection-management-backend-v2.md` Section 2
- pytest configured with fixtures for test DB connections
- Dockerfile for local backend

**Acceptance criteria:**
- `pytest` runs with 0 errors
- `uvicorn local_backend.main:app` starts and `/health` returns `{"status": "ok", "version": "0.1.0"}`
- Docker image builds

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 2, Section 7

---

### Task 1.2: Frontend Project Setup

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/stores/`
- Create: `frontend/src/api/`
- Create: `frontend/src/components/`
- Create: `Dockerfile.frontend`

**What to implement:**
- Vite + React 19 + TypeScript project
- Tailwind CSS configured
- Zustand store skeleton
- API client module with base URL configuration (localhost:8765 for local, configurable for cloud)
- Basic App shell with the 4-panel layout from `docs/04-query-console-design.md` Section 1
- Vitest configured for unit tests

**Acceptance criteria:**
- `npm run dev` starts dev server
- `npm run test` runs with 0 errors
- App renders the 4-panel layout shell (Schema Browser left, Query Console center, AI Chat right, Bottom Drawer)
- Docker image builds

**Spec reference:** `docs/04-query-console-design.md` Section 1

---

### Task 1.3: Cloud Backend Project Setup

**Files:**
- Create: `cloud_backend/main.py`
- Create: `cloud_backend/requirements.txt`
- Create: `cloud_backend/pyproject.toml`
- Create: `cloud_backend/__init__.py`
- Create: `cloud_backend/api/__init__.py`
- Create: `cloud_backend/agents/__init__.py`
- Create: `cloud_backend/sessions/__init__.py`
- Create: `cloud_backend/models/__init__.py`
- Create: `cloud_backend/config.py`
- Create: `tests/cloud_backend/__init__.py`
- Create: `tests/cloud_backend/conftest.py`
- Create: `Dockerfile.cloud`

**What to implement:**
- FastAPI app with CORS, health endpoint
- Project structure matching `docs/07-cloud-backend.md` Section 2
- Config module reading env vars (ANTHROPIC_API_KEY, LLM_MODEL, etc.)
- pytest configured

**Acceptance criteria:**
- `pytest` runs with 0 errors
- `/health` returns `{"status": "ok", "version": "0.1.0"}`
- Docker image builds

**Spec reference:** `docs/07-cloud-backend.md` Sections 2, 7, 8

---

### Task 1.4: Docker Compose for Development

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `.env.example`

**What to implement:**
- Docker compose with 3 services: local_backend, cloud_backend, frontend
- Dev compose with volume mounts for hot reload
- Postgres and MySQL containers for integration tests
- `.env.example` with all required variables

**Acceptance criteria:**
- `docker compose up` starts all 3 services
- Frontend can reach local backend at localhost:8765
- Postgres and MySQL test containers are accessible

---

## Phase 2: Local Backend — Connection Management

### Task 2.1: Connection Models (Pydantic)

**Files:**
- Create: `local_backend/models/connection.py`
- Create: `local_backend/models/common.py`
- Create: `tests/local_backend/test_models_connection.py`

**What to implement:**
- `ConnectionParams` base class with `name`, `db_type`, `validate()`
- `PostgresConnectionParams(host, port, database, username, password)`
- `MySQLConnectionParams(host, port, database, username, password)`
- `BigQueryConnectionParams(project_id, service_account_json)`
- Validation: required fields, port ranges, db_type enum
- Common response models

**Tests:** 7 tests from spec — valid/invalid params per DB type, missing required fields

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 3.1

---

### Task 2.2: Table Identifiers

**Files:**
- Create: `local_backend/models/tables.py`
- Create: `tests/local_backend/test_models_tables.py`

**What to implement:**
- `TableIdentifier` base class with `full_name()`, `to_dict()`, `from_dict()`
- `PostgresTable` → "schema.table"
- `MySQLTable` → "database.table"
- `BigQueryTable` → "project.dataset.table"

**Tests:** 7 tests — full_name() format, serialization roundtrip per DB type

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 3.2

---

### Task 2.3: Entity Exclusion Model

**Files:**
- Create: `local_backend/models/entities.py`
- Create: `tests/local_backend/test_models_entities.py`

**What to implement:**
- `ExclusionConfig` base class with `is_excluded()`, `exclude_entity()`, `include_entity()`, `exclude_all()`, `include_all()`, `sync_new_tables()`
- `PostgresExclusionConfig` (blocked_schemas, blocked_tables)
- `MySQLExclusionConfig` (blocked_databases, blocked_tables)
- `BigQueryExclusionConfig` (blocked_datasets, blocked_tables)
- Resolution logic: table in blocked_tables → excluded, parent in blocked_schemas → excluded, default → included
- No auto-promotion rule
- Parent demotion on single child include

**Tests:** 24 tests from spec — is_excluded variations, exclude/include operations, sync, no auto-promotion, serialization per DB type

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 3.3, `docs/01-connection-management-frontend-v2.md` Entity Exclusion Model

---

### Task 2.4: Config Store

**Files:**
- Create: `local_backend/storage/config_store.py`
- Create: `tests/local_backend/test_config_store.py`

**What to implement:**
- Read/write `~/.sql-debugger/config.json`
- Keyring integration (service `sql-debugger`, key = connection_id)
- `save_connection()`, `load_connection()`, `delete_connection()`, `list_connections()`
- `find_by_name_and_type()` for duplicate check
- `save_exclusions()`, `load_exclusions()`
- `reconcile()` — startup sync (missing passwords → needs_reauth)
- Password never in config.json

**Tests:** 20 tests from spec — save/load/delete, keyring integration, missing password handling, corrupted config, reconcile

**Spec reference:** `docs/02-connection-management-backend-v2.md` Sections 3.4, 4

---

### Task 2.5: Custom Exceptions

**Files:**
- Create: `local_backend/errors/exceptions.py`
- Create: `tests/local_backend/test_errors.py`

**What to implement:**
- `ConnectionNotFoundError`, `DuplicateConnectionError`, `NeedsReauthError`
- `ConfigCorruptedError`, `KeyringAccessError`, `KeyringWriteError`
- `ValidationError`, `InvalidEntityLevelError`

**Tests:** 7 tests — each error exposes expected fields

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 3.7

---

### Task 2.6: Database Adapters — Abstract + Postgres

**Files:**
- Create: `local_backend/db/base.py`
- Create: `local_backend/db/postgres.py`
- Create: `tests/local_backend/test_db_postgres.py`

**What to implement:**
- Abstract `DatabaseAdapter` with `test_connection()`, `list_entities()`, `get_schema()`, `execute()`
- `PostgresAdapter` using psycopg2
- `get_adapter(params)` factory function
- `list_entities()` returns `EntityTree` structure (schemas → tables)
- `get_schema()` returns columns with types from `information_schema.columns`
- Filter out `pg_catalog`, `information_schema` system schemas

**Tests:** 4 integration tests (Docker) — connect valid/invalid, list_entities, execute query

**Spec reference:** `docs/02-connection-management-backend-v2.md` Sections 3.5, `docs/03-schema-browser-frontend.md` Backend Implementation Notes

---

### Task 2.7: Database Adapters — MySQL

**Files:**
- Create: `local_backend/db/mysql.py`
- Create: `tests/local_backend/test_db_mysql.py`

**What to implement:**
- `MySQLAdapter` using mysql-connector-python
- Same interface as PostgresAdapter

**Tests:** 4 integration tests (Docker)

**Spec reference:** Same as 2.6

---

### Task 2.8: Database Adapters — BigQuery

**Files:**
- Create: `local_backend/db/bigquery.py`
- Create: `tests/local_backend/test_db_bigquery.py`

**What to implement:**
- `BigQueryAdapter` using google-cloud-bigquery
- `list_entities()` returns datasets → tables
- `get_schema()` uses region-level `INFORMATION_SCHEMA.COLUMNS`
- Service account JSON parsed from keyring

**Tests:** 4 integration tests (requires BigQuery test project or mocks)

**Spec reference:** Same as 2.6

---

### Task 2.9: Connection Service

**Files:**
- Create: `local_backend/services/connection_service.py`
- Create: `tests/local_backend/test_connection_service.py`

**What to implement:**
- `create_connection()` — UUID generation, duplicate check, save
- `update_connection()` — duplicate check if name changed
- `delete_connection()` — deactivate if active, remove from config + keyring
- `test_connection()` — accepts params or connection_id, 10s timeout
- `activate_connection()`, `get_active_connection()`
- `list_entities(include_columns)` — entity tree + exclusion status merged
- `exclude_entities()`, `include_entities()`, `exclude_all()`, `include_all()`
- Entity level validation per DB type

**Tests:** 16 tests from spec

**Spec reference:** `docs/02-connection-management-backend-v2.md` Section 3.6

---

### Task 2.10: Connection API Endpoints

**Files:**
- Create: `local_backend/api/connections.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_connections.py`

**What to implement:**
- All 14 endpoints from spec (health, CRUD, test, activate, active, entities, exclude/include)
- Error handling: generic messages per security spec
- Password never in responses

**Tests:** 30 integration tests (24 original + 6 new AI tool endpoints)

**Spec reference:** `docs/01-connection-management-frontend-v2.md` Endpoints section, `docs/02-connection-management-backend-v2.md` Section 5

---

## Phase 3: Frontend — Connection Management

### Task 3.1: API Client Module

**Files:**
- Create: `frontend/src/api/localBackend.ts`
- Create: `frontend/src/api/cloudBackend.ts`
- Create: `frontend/src/api/types.ts`

**What to implement:**
- Typed API client for all local backend endpoints
- Base URL configuration (localhost:8765)
- AbortController support for request cancellation
- Error handling (connection refused → local backend not running)
- TypeScript types matching all API request/response schemas

---

### Task 3.2: Connection Store (Zustand)

**Files:**
- Create: `frontend/src/stores/connectionStore.ts`
- Create: `frontend/src/stores/__tests__/connectionStore.test.ts`

**What to implement:**
- Zustand store: connections list, active connection, loading states
- Actions: fetchConnections, createConnection, updateConnection, deleteConnection, testConnection, activateConnection
- Connection switch = full reset (clear all other stores)

---

### Task 3.3: Connection Icon & Panel

**Files:**
- Create: `frontend/src/components/connections/ConnectionIcon.tsx`
- Create: `frontend/src/components/connections/ConnectionPanel.tsx`
- Create: `frontend/src/components/connections/ConnectionCard.tsx`
- Create: `frontend/src/components/connections/__tests__/`

**What to implement:**
- Connection icon in header (green/red/gray dot + name)
- Slide-out panel with connection cards
- Empty state, active badge, action buttons (Edit, Test, Delete, Activate)

**Tests:** UI tests 1-4 from spec

**Spec reference:** `docs/01-connection-management-frontend-v2.md` UI Components 1-2

---

### Task 3.4: Connection Form Modal

**Files:**
- Create: `frontend/src/components/connections/ConnectionForm.tsx`
- Create: `frontend/src/components/connections/EntityTree.tsx`
- Create: `frontend/src/components/connections/__tests__/ConnectionForm.test.tsx`

**What to implement:**
- Connection form with dynamic fields per DB type
- Test Connection button with spinner + latency display
- Entity exclusion tree (hierarchical checkboxes)
- Include All / Exclude All buttons
- Search filter on entity tree
- Review section + Save button
- Edit mode (read-only by default, explicit Edit button)
- Untested save warning dialog

**Tests:** UI tests 5-29 from spec

**Spec reference:** `docs/01-connection-management-frontend-v2.md` UI Components 3-4

---

### Task 3.5: Delete Confirmation & Local Backend Warning

**Files:**
- Create: `frontend/src/components/connections/DeleteDialog.tsx`
- Create: `frontend/src/components/connections/LocalBackendWarning.tsx`

**What to implement:**
- Delete confirmation dialog
- Local backend not running warning with install instructions + Retry button
- Health check polling

**Tests:** UI tests 30-36 from spec

**Spec reference:** `docs/01-connection-management-frontend-v2.md` UI Components 5-6

---

## Phase 4: Local Backend — Schema & Query Endpoints

### Task 4.1: SQL Parser Service (sqlglot)

**Files:**
- Create: `local_backend/services/parser_service.py`
- Create: `tests/local_backend/test_parser_service.py`

**What to implement:**
- Parse SQL → lineage graph (nodes, edges, source positions, node SQL)
- Node types: CTE, subquery, table_source
- Node ID format: CTE → name, table → qualified name, subquery → parent_alias
- Dependency graph + precedence order
- Table name resolution per dialect (Postgres, MySQL, BigQuery)
- Handle: self-joins, UNION branches, recursive CTEs, subqueries in WHERE
- Parse cache in memory (keyed by SQL text)

**Tests:** 20 parse tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 2 (`POST /query/parse`)

---

### Task 4.2: Query Execution Service

**Files:**
- Create: `local_backend/services/query_service.py`
- Create: `tests/local_backend/test_query_service.py`

**What to implement:**
- Execute full query with injection support (AST manipulation via sqlglot)
- WHERE injection: append with AND (or add new WHERE)
- ORDER BY injection: append to node
- Result row limit + truncation flag
- Query timeout
- Request cancellation (request_id → active cursor map)
- Exclusion enforcement: check all table sources against exclusion config

**Tests:** 8 execute tests + 12 execute-node tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Sections 2 (execute, execute-node, cancel)

---

### Task 4.3: Effective SQL Service

**Files:**
- Modify: `local_backend/services/query_service.py`
- Create: `tests/local_backend/test_effective_sql.py`

**What to implement:**
- Build effective SQL with all injections applied, without executing
- Uses same injection logic as execute

**Tests:** 5 effective-sql tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 2 (`POST /query/effective-sql`)

---

### Task 4.4: Query API Endpoints

**Files:**
- Create: `local_backend/api/query.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_query.py`

**What to implement:**
- `POST /query/parse` — parse SQL, cache result
- `POST /connections/{id}/execute` — execute with injections
- `POST /connections/{id}/execute-node` — execute node subtree
- `POST /query/effective-sql` — return modified SQL
- `POST /connections/{id}/cancel` — cancel running query

**Tests:** 3 cancel tests from spec + integration tests

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 2

---

## Phase 5: Frontend — Schema Browser

### Task 5.1: Schema Store & Cache

**Files:**
- Create: `frontend/src/stores/schemaStore.ts`
- Create: `frontend/src/stores/__tests__/schemaStore.test.ts`

**What to implement:**
- Zustand store: schema tree, loading state, error state
- localStorage cache: `schema_cache_{connection_id}`
- Stale-while-revalidate: show cache immediately, fetch in background
- Cache invalidation on connection delete, manual refresh, DDL detected
- Auto-refresh triggers: connection select, page load, DDL, exclusion change

**Spec reference:** `docs/03-schema-browser-frontend.md` Data Flow section

---

### Task 5.2: Schema Browser Panel

**Files:**
- Create: `frontend/src/components/schema/SchemaBrowser.tsx`
- Create: `frontend/src/components/schema/SchemaTree.tsx`
- Create: `frontend/src/components/schema/SchemaNode.tsx`
- Create: `frontend/src/components/schema/__tests__/`

**What to implement:**
- Toggle button in toolbar (opens/closes panel)
- Tree hierarchy per DB type (Postgres: schema→table→column, MySQL: database→table→column, BigQuery: dataset→table→column)
- Expand/collapse nodes
- Column types right-aligned, muted monospace, truncated with tooltip
- Excluded entities: grey text + ⊘ icon + tooltip
- Search filter (schema and table names, case-insensitive)
- Summary footer (X tables, Y excluded)
- All states: no connection, loading, cached+refreshing, error, empty, search no results

**Tests:** 45 tests from spec (25 unit + 20 integration)

**Spec reference:** `docs/03-schema-browser-frontend.md` UI Components, Tests

---

## Phase 6: Frontend — Query Console

### Task 6.1: SQL Editor (CodeMirror 6)

**Files:**
- Create: `frontend/src/components/editor/SqlEditor.tsx`
- Create: `frontend/src/components/editor/gutterButtons.ts`
- Create: `frontend/src/components/editor/highlightSync.ts`
- Create: `frontend/src/components/editor/__tests__/`

**What to implement:**
- CodeMirror 6 with SQL syntax highlighting
- Background re-parse: 300ms debounce after typing stops, calls `/query/parse`
- Gutter run buttons (▶) on hover for recognized SQL spans (CTEs, subqueries, table sources)
- Overlapping spans: innermost node priority, right-click for enclosing nodes
- Highlight sync: click editor span → highlight lineage node
- Context menu: Execute, Add filter, Show in lineage

**Tests:** 8 editor tests + 10 inline execution tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Sections 3, 7, 8

---

### Task 6.2: Action Bar & File Upload

**Files:**
- Create: `frontend/src/components/editor/ActionBar.tsx`
- Create: `frontend/src/components/editor/__tests__/ActionBar.test.tsx`

**What to implement:**
- [Visualize] button → calls parse, opens lineage tab
- [Run ▶] button → calls execute with SQL + injections, opens results tab. Disabled when no active connection.
- [Upload .sql] → file picker, replaces editor content
- [Cancel] → visible during execution, cancels all active request_ids
- All buttons disabled + spinner during operations

**Tests:** 7 action bar tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 3

---

### Task 6.3: Parse & Execution Stores

**Files:**
- Create: `frontend/src/stores/parseStore.ts`
- Create: `frontend/src/stores/executionStore.ts`
- Create: `frontend/src/stores/__tests__/`

**What to implement:**
- Parse store: parseResult (background re-parse), visualGraph (explicit Visualize), isGraphStale
- Execution store: executionResults map, activeExecutions map, activeResultTab
- Request ID generation, cancellation tracking

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Key State section

---

## Phase 7: Frontend — Lineage Visualization

### Task 7.1: React Flow + ELK Setup

**Files:**
- Create: `frontend/src/components/lineage/LineageGraph.tsx`
- Create: `frontend/src/components/lineage/elkLayout.ts`
- Create: `frontend/src/components/lineage/__tests__/`

**What to implement:**
- React Flow canvas with ELK layout engine
- Convert parse result (nodes + edges) to React Flow format
- Dependency graph layout (sources at top, data flows down)
- Precedence graph layout (narrative order)
- Zoom, pan, standard graph interaction

---

### Task 7.2: Lineage Nodes

**Files:**
- Create: `frontend/src/components/lineage/LineageNode.tsx`
- Create: `frontend/src/components/lineage/nodeStyles.ts`

**What to implement:**
- Color-coded nodes: Blue=CTE, Purple=Subquery, Green=Table
- Node content: status indicator (○/●/✓/✗/⟳), name, quick execute [▶], filter indicator
- Hover: highlight node + direct edges, tooltip with type label
- Click: select node, highlight SQL span in editor (bidirectional sync)
- Double-click: execute node
- Right-click: context menu (execute, breakpoint, filter, collapse, show in editor)
- Collapsed subtree: [+N] badge

**Tests:** 18 lineage graph tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Sections 4, 5

---

### Task 7.3: Lineage Toolbar & Graph Modes

**Files:**
- Create: `frontend/src/components/lineage/LineageToolbar.tsx`

**What to implement:**
- Graph mode toggle (Dependency / Precedence)
- Breakpoint type filter (CTEs / Tables / Subqueries) — only visible when breakpoints set
- [Run Breakpoints] [Clear Breakpoints] buttons
- [Expand All] [Collapse All] buttons
- Staleness banner: "Graph outdated — click Visualize to refresh"

---

### Task 7.4: Breakpoints

**Files:**
- Create: `frontend/src/stores/breakpointStore.ts`
- Create: `frontend/src/components/lineage/__tests__/breakpoints.test.tsx`

**What to implement:**
- Toggle breakpoint on node (click indicator or right-click)
- Breakpoint upstream (all ancestors) / downstream (all dependents)
- Type filter: toggle off/on node types
- Run Breakpoints: parallel execute-node calls, wait for all
- Results navigation: first tab shown, [Next] advances, [Show All] reveals all
- Tab order matches graph mode

**Tests:** 15 breakpoint tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 6

---

### Task 7.5: Bidirectional Sync

**Files:**
- Modify: `frontend/src/components/editor/highlightSync.ts`
- Create: `frontend/src/stores/syncStore.ts`

**What to implement:**
- Lineage → Console: click node → scroll to + highlight SQL span
- Console → Lineage: click/select SQL span → highlight matching lineage node
- Background re-parse keeps positions accurate
- Failure handling: use last known good positions when parse fails

**Tests:** 5 bidirectional sync tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 8

---

### Task 7.6: Graph Collapse & Focus

**Files:**
- Modify: `frontend/src/components/lineage/LineageGraph.tsx`
- Create: `frontend/src/stores/graphViewStore.ts`

**What to implement:**
- Collapsible subtrees: right-click → collapse, children hidden, [+N] badge
- "Show in lineage" from editor: scroll to node, dim distant nodes, click background to un-dim
- Smart default: ≤12 nodes fully expanded, 13+ auto-collapsed

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 10

---

## Phase 8: Frontend — Results Viewer & Injection

### Task 8.1: Results Viewer

**Files:**
- Create: `frontend/src/components/results/ResultsViewer.tsx`
- Create: `frontend/src/components/results/ResultTabBar.tsx`
- Create: `frontend/src/components/results/ResultTable.tsx`
- Create: `frontend/src/components/results/__tests__/`

**What to implement:**
- TanStack Table integration
- Tab management: node tabs + "Full Query" tab, each independent
- Per-tab: column sort (click header), column filter, row count, execution time
- Truncated results message
- NULL display: muted italic grey
- Long cell values: truncated, click to expand
- [Copy CSV] [Copy JSON] export
- States: loading, success, error (with Copy Error), cancelled, empty (0 rows)

**Tests:** 12 results viewer tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 11

---

### Task 8.2: Filter & Order Injection Panel

**Files:**
- Create: `frontend/src/components/injection/FilterOrderPanel.tsx`
- Create: `frontend/src/components/injection/InjectionStatusBar.tsx`
- Create: `frontend/src/stores/injectionStore.ts`
- Create: `frontend/src/components/injection/__tests__/`

**What to implement:**
- Injection store: Map<nodeId, {where?, order_by?}> in sessionStorage
- Status bar: "⚡ N filters active" + [View effective SQL]
- Panel: table with Node | WHERE | ORDER BY | [×] columns
- Inline editing of WHERE and ORDER BY cells
- [+ Add filter] with node dropdown
- [Clear All] removes all injections
- [View effective SQL] modal (calls `/query/effective-sql`)
- Stale entries: silently drop if node ID no longer exists after re-parse

**Tests:** 9 filter panel tests from spec

**Spec reference:** `docs/05-query-console-lineage-detailed.md` Section 9

---

## Phase 9: Local Backend — AI Support Endpoints

### Task 9.1: Table Profile Endpoint

**Files:**
- Create: `local_backend/api/ai_support.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `GET /connections/{id}/tables/{table}/profile`
- Generates: `SELECT COUNT(*), COUNT(DISTINCT col), MIN(col), MAX(col), SUM(CASE WHEN col IS NULL THEN 1 ELSE 0 END)` per column
- Min/max only for numeric and date/timestamp types
- Exclusion enforcement: reject excluded tables with 403

**Tests:** 2 tests (profile returns stats, excluded table returns 403)

**Spec reference:** `docs/02-connection-management-backend-v2.md` AI Agent Support Endpoints

---

### Task 9.2: Indexes Endpoint

**Files:**
- Modify: `local_backend/api/ai_support.py`
- Modify: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `GET /connections/{id}/tables/{table}/indexes`
- Postgres: `pg_constraint`, `pg_index`
- MySQL: `information_schema.key_column_usage`
- BigQuery: partitioning + clustering info (no traditional indexes)
- Exclusion enforcement: 403 on excluded tables

**Tests:** 2 tests (indexes returns data, excluded table returns 403)

**Spec reference:** `docs/02-connection-management-backend-v2.md` AI Agent Support Endpoints

---

### Task 9.3: Sample Endpoint

**Files:**
- Modify: `local_backend/api/ai_support.py`
- Modify: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `POST /connections/{id}/sample`
- `SELECT * FROM table LIMIT N`
- Exclusion enforcement: 403 on excluded tables

**Tests:** 2 tests (sample returns rows, excluded table returns 403)

**Spec reference:** `docs/02-connection-management-backend-v2.md` AI Agent Support Endpoints

---

## Phase 10: Cloud Backend

### Task 10.1: Session Management

**Files:**
- Create: `cloud_backend/sessions/session_store.py`
- Create: `cloud_backend/models/session.py`
- Create: `tests/cloud_backend/test_session_store.py`

**What to implement:**
- In-memory session map: `session_id → SessionState`
- Session creation (chat and debug)
- Session lookup, status tracking (active, waiting_tool, completed, cancelled, error)
- One debug session at a time enforcement
- Session timeout (30 min inactive)
- Background cleanup task
- Query count and LLM call count tracking

**Tests:** 9 session tests from spec (tests 1-9)

**Spec reference:** `docs/07-cloud-backend.md` Section 4

---

### Task 10.2: SSE Streaming & Event Registry

**Files:**
- Create: `cloud_backend/sessions/sse_registry.py`
- Create: `cloud_backend/models/events.py`
- Create: `cloud_backend/api/sessions.py`
- Create: `tests/cloud_backend/test_sse.py`

**What to implement:**
- SSE registry: `session_id → open SSE connection`
- Event types: progress, tool_call, chat_response, chat_response_end, conclusion, error
- `GET /sessions/{id}/stream` — SSE endpoint
- `POST /sessions/{id}/respond` — route tool result to session
- `POST /sessions/{id}/cancel` — cancel session
- Event log per session for reconnection replay
- Sequence numbers for missed event detection

**Tests:** 6 SSE tests from spec (tests 10-15)

**Spec reference:** `docs/07-cloud-backend.md` Sections 3, 4

---

### Task 10.3: Chat & Debug API Endpoints

**Files:**
- Create: `cloud_backend/api/chat.py`
- Create: `cloud_backend/api/debug.py`
- Modify: `cloud_backend/main.py` (register routers)
- Create: `tests/cloud_backend/test_api_chat.py`
- Create: `tests/cloud_backend/test_api_debug.py`

**What to implement:**
- `POST /chat/sessions` — create chat session with context
- `POST /chat/{id}/message` — send message, triggers agent
- `POST /debug/sessions` — create debug session, start investigation
- Context injection: query text, lineage, schema, excluded tables, DB type
- Debug: bug category, details, hint

**Spec reference:** `docs/07-cloud-backend.md` Section 3

---

### Task 10.4: Agent Tools (Cloud-side Wrappers)

**Files:**
- Create: `cloud_backend/agents/tools/validate_query.py`
- Create: `cloud_backend/agents/tools/execute_query.py`
- Create: `cloud_backend/agents/tools/get_schema.py`
- Create: `cloud_backend/agents/tools/get_node_results.py`
- Create: `cloud_backend/agents/tools/get_lineage.py`
- Create: `cloud_backend/agents/tools/table_profile.py`
- Create: `cloud_backend/agents/tools/get_indexes.py`
- Create: `cloud_backend/agents/tools/sample_data.py`
- Create: `tests/cloud_backend/test_agent_tools.py`

**What to implement:**
- Each tool emits a `tool_call` SSE event and waits for `/respond`
- `validate_query`: parse + exclusion check + SELECT-only. Reject SELECT *, return available columns.
- `execute_query`: validate first, cap results at 50 rows, truncate cells at 200 chars
- `get_schema`: filter out excluded tables from response
- `get_node_results`: check subtree for excluded tables
- `get_lineage`: return from session state (no endpoint call)
- `table_profile`, `get_indexes`, `sample_data`: reject excluded tables, format for LLM

**Tests:** 12 tool mapping tests from spec (tests 16-27)

**Spec reference:** `docs/07-cloud-backend.md` Section 5, `docs/06-ai-chat-and-debugging.md` Sections 4.1, 5.1

---

### Task 10.5: Chat Agent (LangGraph)

**Files:**
- Create: `cloud_backend/agents/chat_agent.py`
- Create: `tests/cloud_backend/test_chat_agent.py`

**What to implement:**
- LangGraph graph: generate response with tools → stream to frontend
- System prompt: role, context, tools, allowed/blocked topics, DB dialect, soft redirect to debug
- Tools: table_profile, get_indexes, sample_data
- Streaming: chunk responses via SSE (chat_response events)
- Tool results inline in response (no tool usage indicator to user)

**Tests:** 7 chat guardrail tests from spec (tests 47-53)

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Sections 5, 8

---

### Task 10.6: Debug Agent (LangGraph)

**Files:**
- Create: `cloud_backend/agents/debug_agent.py`
- Create: `tests/cloud_backend/test_debug_agent.py`

**What to implement:**
- LangGraph state machine: plan → execute → analyze → (loop or report)
- System prompt: role, context, investigation rules, verdicts, query rules, report format, limits
- Tools: validate_query, execute_query, get_schema, get_node_results, get_lineage
- Session limits: 15 queries, 3 retries, 20 LLM calls
- Verdicts: query_bug, expected_behavior, potential_data_bug
- Report structure: conclusion → investigation steps (with evidence) → next steps → limitations
- Progress events during investigation

**Tests:** 3 debug limit tests (tests 28-30) + 3 cancel tests (tests 31-33)

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Sections 4, 8, `docs/07-cloud-backend.md` Section 6

---

## Phase 11: Frontend — AI Chat & Debug

### Task 11.1: SSE Client & Chat Store

**Files:**
- Create: `frontend/src/api/sseClient.ts`
- Create: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/stores/__tests__/chatStore.test.ts`

**What to implement:**
- SSE client: connect to `/sessions/{id}/stream`, handle event types, auto-reconnect
- Chat store: sessions list, active session, messages, loading states
- Tab management: multiple chat tabs, one debug at a time
- Tool call handling: receive tool_call event → call local backend → POST /respond

---

### Task 11.2: Chat Panel UI

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.tsx`
- Create: `frontend/src/components/chat/ChatTabs.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/chat/ContextIndicator.tsx`
- Create: `frontend/src/components/chat/__tests__/`

**What to implement:**
- Right sidebar panel, hidden by default, toggleable
- Mode dropdown: Chat / Debug
- Tab management: [+] button, tab switching, close tab
- Context indicator: query status, CTE count, schema summary
- Chat mode: message input, streamed response display, scrollable history
- Inline data tables in responses (5×5 scrollable viewport)

**Tests:** UI tests 54-66 from spec

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Section 6

---

### Task 11.3: Debug Wizard

**Files:**
- Create: `frontend/src/components/chat/DebugWizard.tsx`
- Create: `frontend/src/components/chat/__tests__/DebugWizard.test.tsx`

**What to implement:**
- Step 1: Category selection (row count, nulls, values, missing columns, duplicate columns)
- Step 2: Category-specific follow-up (structured options + free text)
- Step 3: Hint (optional free text)
- Step 4: Go → creates debug session, starts investigation
- Blocked states: no query loaded, syntax errors

**Tests:** UI tests 67-73 from spec

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Section 4.2, 6.6

---

### Task 11.4: Debug Progress & Report

**Files:**
- Create: `frontend/src/components/chat/DebugProgress.tsx`
- Create: `frontend/src/components/chat/DebugReport.tsx`
- Create: `frontend/src/components/chat/__tests__/DebugReport.test.tsx`

**What to implement:**
- Progress: action summaries appearing one by one, "This may take a few minutes", Cancel button
- Sound notification on completion
- Badge indicator on debug tab when report ready
- Report: verdict display, ordered investigation steps, expandable evidence (query + results table), back-references ("see step 2"), observations with ⚠ marker, next steps, limitations

**Tests:** UI tests 74-85 from spec

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Sections 4.5, 4.8, 6

---

### Task 11.5: Edge Cases & Connection Switch

**Files:**
- Modify: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/components/chat/__tests__/edgeCases.test.tsx`

**What to implement:**
- Connection switch: cancel debug, clear chat sessions, show cancellation message
- Query edited during debug: banner "Query changed since debug started"
- All tables excluded: block debug
- SSE disconnect: auto-reconnect
- LLM API error: retry once, then show error
- Second debug session: blocked with message

**Tests:** UI tests 86-93 from spec

**Spec reference:** `docs/06-ai-chat-and-debugging.md` Section 9

---

## Phase 12: Integration & Polish

### Task 12.1: Connection Switch Full Reset

**Files:**
- Modify: `frontend/src/stores/connectionStore.ts`
- Modify: all other stores

**What to implement:**
- When active connection changes: AbortController cancels all in-flight requests
- Clear: schema cache, lineage graph, parse cache, results tabs, injections, chat/debug sessions
- Each store exposes a `reset()` method, connectionStore calls all on switch

**Spec reference:** `docs/project-overview.md` Project-wide Rules

---

### Task 12.2: End-to-End Flow Tests

**Files:**
- Create: `tests/e2e/test_connection_flow.py`
- Create: `tests/e2e/test_query_debug_flow.py`

**What to implement:**
- Full flow: create connection → test → save → activate → browse schema → paste query → visualize → execute node → add filter → run debug → get report
- Connection switch mid-flow: verify full reset
- Error flows: local backend down, cloud backend down, DB unreachable

---

### Task 12.3: Docker Compose Production

**Files:**
- Modify: `docker-compose.yml`
- Create: `docker-compose.prod.yml`

**What to implement:**
- Production compose: frontend served from cloud backend (or separate CDN)
- CORS configuration: cloud frontend origin → local backend
- Environment variable configuration for Railway/Render

---

## Summary

| Phase | Tasks | Est. Tests |
|-------|-------|-----------|
| 1. Scaffolding | 4 | ~10 |
| 2. Local Backend — Connections | 10 | ~132 |
| 3. Frontend — Connections | 5 | ~36 |
| 4. Local Backend — Schema & Query | 4 | ~48 |
| 5. Frontend — Schema Browser | 2 | ~45 |
| 6. Frontend — Query Console | 3 | ~25 |
| 7. Frontend — Lineage | 6 | ~38 |
| 8. Frontend — Results & Injection | 2 | ~21 |
| 9. Local Backend — AI Endpoints | 3 | ~6 |
| 10. Cloud Backend | 6 | ~33 |
| 11. Frontend — AI Chat & Debug | 5 | ~40 |
| 12. Integration & Polish | 3 | ~10 |
| **Total** | **53 tasks** | **~444 tests** |
