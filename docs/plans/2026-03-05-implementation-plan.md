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
    |
Phase 2: Local Backend -- Connection Management
    |                    \
Phase 3: Frontend --       Phase 4: Local Backend --
  Connection Mgmt           Schema & Query Endpoints
    |                    /
Phase 5: Frontend -- Schema Browser
    |
Phase 6: Frontend -- Query Console (Editor)
    |
Phase 7: Frontend -- Lineage Visualization
    |
Phase 8: Frontend -- Results Viewer & Injection
    |                    \
Phase 9: Local Backend --  Phase 10: Cloud Backend
  AI Support Endpoints       (Sessions, SSE, LangGraph)
    |                    /
Phase 11: Frontend -- AI Chat & Debug
    |
Phase 12: Integration & Polish
```

Phases 2 and 4 can run in parallel after Phase 1.
Phases 9 and 10 can run in parallel after Phase 8.

---

## Phase 1: Project Scaffolding

### Task 1.1: Local Backend Project Setup

**Purpose:** Set up the Python/FastAPI project that runs on the user's machine. This is the security-critical backend that holds DB credentials and executes queries — it never exposes credentials to the network.

**Context:** The local backend is the foundation for all database operations. Every query, schema fetch, and connection test goes through here. The health endpoint is how the frontend detects whether the local backend is running.

**Files:**
- Create: `local_backend/main.py`, `local_backend/requirements.txt`, `local_backend/pyproject.toml`
- Create: `local_backend/__init__.py`, `local_backend/api/__init__.py`, `local_backend/models/__init__.py`, `local_backend/services/__init__.py`, `local_backend/db/__init__.py`, `local_backend/storage/__init__.py`, `local_backend/errors/__init__.py`
- Create: `tests/local_backend/__init__.py`, `tests/local_backend/conftest.py`
- Create: `Dockerfile.local`

**What to implement:**
- FastAPI app with CORS middleware, health endpoint (`GET /health`)
- Project structure matching spec
- pytest configured with fixtures for test DB connections
- Dockerfile for local backend

**Acceptance criteria:**
- `pytest` runs with 0 errors
- `uvicorn local_backend.main:app` starts and `/health` returns `{"status": "ok", "version": "0.1.0"}`
- Docker image builds

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 2 (Project Structure), Section 7 (Config)

---

### Task 1.2: Frontend Project Setup

**Purpose:** Set up the React/TypeScript app that users interact with. The frontend loads from the cloud but runs entirely in the browser, talking to both the local backend (for DB operations) and the cloud backend (for AI reasoning).

**Context:** The frontend is the central hub — it coordinates between local and cloud backends, proxies tool calls for the AI agent, and renders all UI. The 4-panel layout (Schema Browser left, Query Console center, AI Chat right, Results bottom) is the main workspace users spend all their time in.

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/tailwind.config.ts`, `frontend/postcss.config.js`, `frontend/index.html`
- Create: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`
- Create: `frontend/src/stores/`, `frontend/src/api/`, `frontend/src/components/`
- Create: `Dockerfile.frontend`

**What to implement:**
- Vite + React 19 + TypeScript project
- Tailwind CSS configured
- Zustand store skeleton
- API client module with base URL configuration (localhost:8765 for local, configurable for cloud)
- Basic App shell with the 4-panel layout
- Vitest configured for unit tests

**Acceptance criteria:**
- `npm run dev` starts dev server
- `npm run test` runs with 0 errors
- App renders the 4-panel layout shell
- Docker image builds

**Spec:** `docs/04-query-console-design.md` → Section 1 (Layout)

---

### Task 1.3: Cloud Backend Project Setup

**Purpose:** Set up the FastAPI server that hosts AI reasoning. This runs in the cloud (Railway/Render) and never sees DB credentials or query results — it only receives query text, lineage, and schema for AI analysis.

**Context:** The cloud backend manages chat/debug sessions, runs LangGraph agents, and streams responses via SSE. When the agent needs data (e.g., execute a query), it emits a tool_call event — the frontend handles the actual execution via the local backend and posts results back.

**Files:**
- Create: `cloud_backend/main.py`, `cloud_backend/requirements.txt`, `cloud_backend/pyproject.toml`
- Create: `cloud_backend/__init__.py`, `cloud_backend/api/__init__.py`, `cloud_backend/agents/__init__.py`, `cloud_backend/sessions/__init__.py`, `cloud_backend/models/__init__.py`, `cloud_backend/config.py`
- Create: `tests/cloud_backend/__init__.py`, `tests/cloud_backend/conftest.py`
- Create: `Dockerfile.cloud`

**What to implement:**
- FastAPI app with CORS, health endpoint
- Config module reading env vars (ANTHROPIC_API_KEY, LLM_MODEL, etc.)
- pytest configured

**Acceptance criteria:**
- `pytest` runs with 0 errors
- `/health` returns `{"status": "ok", "version": "0.1.0"}`
- Docker image builds

**Spec:** `docs/07-cloud-backend.md` → Sections 2 (Architecture), 7–8 (Config, Deployment)

---

### Task 1.4: Docker Compose for Development

**Purpose:** One-command setup to run all 3 services plus test databases. This is how developers (and CI) run the full stack locally.

**Context:** The dev compose needs hot reload (volume mounts) for all services, plus Postgres and MySQL containers for integration tests. BigQuery tests use mocks since there's no local BigQuery emulator.

**Files:**
- Create: `docker-compose.yml`, `docker-compose.dev.yml`, `.env.example`

**What to implement:**
- Docker compose with 3 services: local_backend, cloud_backend, frontend
- Dev compose with volume mounts for hot reload
- Postgres and MySQL containers for integration tests
- `.env.example` with all required variables

**Acceptance criteria:**
- `docker compose up` starts all 3 services
- Frontend can reach local backend at localhost:8765
- Postgres and MySQL test containers are accessible

**Spec:** `docs/project-overview.md` → Architecture section

---

## Phase 2: Local Backend — Connection Management

### Task 2.1: Connection Models (Pydantic)

**Purpose:** Define the data shapes for database connections. Each DB type (Postgres, MySQL, BigQuery) has different credentials, so we need type-specific models with validation — this prevents users from saving invalid configurations.

**Context:** These models are used everywhere: the API layer validates incoming requests against them, the ConfigStore serializes them to disk, and the DatabaseAdapter factory uses `db_type` to pick the right adapter. Validation only runs on create/update/test — not when loading from config (to avoid blocking startup if validation rules change).

**Files:**
- Create: `local_backend/models/connection.py`
- Create: `local_backend/models/common.py`
- Create: `tests/local_backend/test_models_connection.py`

**What to implement:**
- `ConnectionParams` base class with `name`, `db_type`, `validate()`
- `PostgresConnectionParams(host, port, database, username, password)`
- `MySQLConnectionParams(host, port, database, username, password)`
- `BigQueryConnectionParams(project_id, service_account_json)`
- Validation: required fields, port ranges (1–65535), db_type enum
- Common response models (e.g., `ConnectionSummary` without password)

**Tests (7):** Valid/invalid params per DB type, missing required fields, port range validation

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.1 (ConnectionParams)

---

### Task 2.2: Table Identifiers

**Purpose:** Represent fully-qualified table names across different DB types. Each DB has a different naming scheme (Postgres: schema.table, BigQuery: project.dataset.table), and we need a consistent interface for the exclusion system and sqlglot integration.

**Context:** Table identifiers are used by the ExclusionConfig to check access, by sqlglot for name resolution in lineage parsing, and by the API to reference specific tables (e.g., AI agent endpoints like `/tables/{table}/profile`).

**Files:**
- Create: `local_backend/models/tables.py`
- Create: `tests/local_backend/test_models_tables.py`

**What to implement:**
- `TableIdentifier` base class with `full_name()`, `to_dict()`, `from_dict()`
- `PostgresTable` → "schema.table"
- `MySQLTable` → "database.table"
- `BigQueryTable` → "project.dataset.table"

**Tests (7):** full_name() format per DB type, serialization roundtrip, from_dict with wrong type

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.2 (TableIdentifier)

---

### Task 2.3: Entity Exclusion Model

**Purpose:** Control which tables the AI agent can access. Users check/uncheck tables in a tree UI, and this model tracks what's blocked. This is a core security feature — excluded tables are invisible to the AI agent and rejected by all query execution.

**Context:** The exclusion model uses denormalized storage for O(1) lookups: `blocked_schemas` + `blocked_tables` (per-parent). Key design decision: no auto-promotion — individually excluding all tables in a schema does NOT auto-add the schema to `blocked_schemas`. This matters because new tables discovered in a non-blocked schema won't be auto-excluded. Parent demotion happens when you include a single table from an excluded schema — the schema is removed from `blocked_schemas` and all other tables are individually added to `blocked_tables`.

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

**Tests (24):** is_excluded variations, exclude/include operations, sync_new_tables, no auto-promotion, parent demotion, serialization per DB type

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.3 (ExclusionConfig), `docs/01-connection-management-frontend-v2.md` → Entity Exclusion Model

---

### Task 2.4: Config Store

**Purpose:** Persist connection configs to disk and passwords to the OS keyring. This is the storage layer that ensures credentials survive app restarts while keeping passwords out of plain-text config files.

**Context:** Config lives at `~/.sql-debugger/config.json` — it stores connection metadata, exclusion rules, and everything except passwords. Passwords go to the OS keyring (macOS Keychain, Windows Credential Manager, Linux SecretService) keyed by connection UUID. On startup, `reconcile()` checks that every connection in config has a matching keyring entry — missing passwords get flagged as `needs_reauth` so the UI can prompt the user.

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

**Tests (20):** Save/load/delete, keyring integration, missing password handling, corrupted config, reconcile, password never in config file

**Spec:** `docs/02-connection-management-backend-v2.md` → Sections 3.4 (ConfigStore), 4 (Storage Format)

---

### Task 2.5: Custom Exceptions

**Purpose:** Define typed errors for the connection management domain. Each error carries structured data (e.g., which connection_id wasn't found) so API handlers can return appropriate HTTP status codes and messages.

**Context:** These exceptions are raised by the ConnectionService and caught by the API layer. The API converts them to HTTP responses with generic messages (security requirement — don't leak internal details like "wrong password" vs "host unreachable").

**Files:**
- Create: `local_backend/errors/exceptions.py`
- Create: `tests/local_backend/test_errors.py`

**What to implement:**
- `ConnectionNotFoundError`, `DuplicateConnectionError`, `NeedsReauthError`
- `ConfigCorruptedError`, `KeyringAccessError`, `KeyringWriteError`
- `ValidationError`, `InvalidEntityLevelError`

**Tests (7):** Each error exposes expected fields (e.g., connection_id, field name, allowed_levels)

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.7 (Error Types)

---

### Task 2.6: Database Adapters — Abstract + Postgres

**Purpose:** Define the interface that all database adapters implement, then build the Postgres adapter. This is how the app actually talks to databases — every connection test, schema fetch, and query execution goes through an adapter.

**Context:** The abstract `DatabaseAdapter` defines 4 methods: `test_connection()`, `list_entities()`, `get_schema()`, `execute()`. The factory function `get_adapter(params)` returns the right subclass based on `db_type`. The Postgres adapter uses psycopg2 and filters out system schemas (`pg_catalog`, `information_schema`) from entity listings. `list_entities()` returns a hierarchical `EntityTree` (schemas → tables) that the Schema Browser renders directly.

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

**Tests (4):** Integration tests (Docker) — connect valid/invalid, list_entities structure, execute query

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.5 (DatabaseAdapter), `docs/03-schema-browser-frontend.md` → Backend Implementation Notes

---

### Task 2.7: Database Adapters — MySQL

**Purpose:** Build the MySQL adapter so the app can connect to MySQL databases. Same interface as Postgres, different driver and SQL dialect.

**Context:** Uses mysql-connector-python. MySQL's hierarchy is database→table (no schema level). `list_entities()` returns databases → tables. System databases (`information_schema`, `mysql`, `performance_schema`, `sys`) should be filtered out.

**Files:**
- Create: `local_backend/db/mysql.py`
- Create: `tests/local_backend/test_db_mysql.py`

**What to implement:**
- `MySQLAdapter` using mysql-connector-python
- Same interface as PostgresAdapter

**Tests (4):** Integration tests (Docker) — connect valid/invalid, list_entities, execute query

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.5 (DatabaseAdapter)

---

### Task 2.8: Database Adapters — BigQuery

**Purpose:** Build the BigQuery adapter for Google Cloud users. BigQuery has a different model — no traditional server connection, uses service account JSON, and schema queries go through region-level INFORMATION_SCHEMA.

**Context:** Uses google-cloud-bigquery client. BigQuery's hierarchy is project→dataset→table. Authentication is via service account JSON stored in the keyring. `list_entities()` returns datasets → tables. A single region-level `INFORMATION_SCHEMA.COLUMNS` query returns all datasets — same efficiency as other adapters.

**Files:**
- Create: `local_backend/db/bigquery.py`
- Create: `tests/local_backend/test_db_bigquery.py`

**What to implement:**
- `BigQueryAdapter` using google-cloud-bigquery
- `list_entities()` returns datasets → tables
- `get_schema()` uses region-level `INFORMATION_SCHEMA.COLUMNS`
- Service account JSON parsed from keyring

**Tests (4):** Integration tests (requires BigQuery test project or mocks)

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.5 (DatabaseAdapter)

---

### Task 2.9: Connection Service

**Purpose:** Orchestrate all connection operations — the business logic layer between API endpoints and storage/adapters. This is where rules like "duplicate names are rejected" and "deleting an active connection deactivates it first" live.

**Context:** The service coordinates ConfigStore (persistence), DatabaseAdapters (connectivity), and ExclusionConfig (access control). It also merges entity trees with exclusion status for the Schema Browser and validates entity levels per DB type (e.g., you can't exclude a "schema" on MySQL — MySQL only has databases and tables).

**Files:**
- Create: `local_backend/services/connection_service.py`
- Create: `tests/local_backend/test_connection_service.py`

**What to implement:**
- `create_connection()` — UUID generation, duplicate check (name+type), save to config + keyring
- `update_connection()` — duplicate check if name changed
- `delete_connection()` — deactivate if active, remove from config + keyring
- `test_connection()` — accepts params or connection_id, 10s timeout, returns success + latency
- `activate_connection()`, `get_active_connection()`
- `list_entities(include_columns)` — entity tree + exclusion status merged
- `exclude_entities()`, `include_entities()`, `exclude_all()`, `include_all()`
- Entity level validation per DB type

**Tests (16):** Create/update/delete flows, duplicate check, test valid/invalid, activate/deactivate, list entities with exclusions, entity level validation errors

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 3.6 (ConnectionService)

---

### Task 2.10a: Connection CRUD & Health API

**Purpose:** Expose core connection management over HTTP — this is how the frontend creates, reads, updates, and deletes saved database connections. The health endpoint lets the frontend detect whether the local backend is running.

**Context:** The ConnectionService (Task 2.9) handles all business logic. This task is a thin FastAPI layer that routes HTTP requests to that service and formats responses. Passwords must never appear in API responses (security invariant).

**Files:**
- Create: `local_backend/api/connections.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_connections.py`

**What to implement:**
- `GET /health` — frontend polls this to show "local backend not running" warning
- `GET /connections` — list all saved connections (for the connection panel)
- `POST /connections` — create new connection (from the connection form)
- `GET /connections/{id}` — get single connection details (for edit form)
- `PUT /connections/{id}` — update connection (from edit mode)
- `DELETE /connections/{id}` — remove connection (deactivates first if active)
- Error handling: generic messages per security spec

**Tests (~12):** Valid CRUD operations, 404 on missing ID, duplicate name rejection, password not in response body

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 5 (API Endpoints), CRUD endpoints table

---

### Task 2.10b: Connection Lifecycle API

**Purpose:** Let the frontend test database connectivity before saving, activate a connection to make it the "current working connection," and check which connection is active. These are the actions that happen after CRUD — the user creates a connection, tests it, then activates it to start working.

**Context:** Testing a connection uses the DatabaseAdapter (Tasks 2.6–2.8) to actually connect to the DB with a 10-second timeout. Activating a connection sets it as the single active connection — the frontend uses this to know which DB to query against. Only one connection can be active at a time.

**Files:**
- Modify: `local_backend/api/connections.py`
- Modify: `tests/local_backend/test_api_connections.py`

**What to implement:**
- `POST /connections/test` — accepts raw params (before saving) or connection_id (after saving), returns success/failure + latency
- `POST /connections/{id}/activate` — sets this connection as active, deactivates previous
- `GET /connections/active` — returns the currently active connection (used on page load to restore state)

**Tests (~8):** Test with valid/invalid credentials, test with connection_id, activate/deactivate, get active when none set

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 5 (API Endpoints), lifecycle endpoints table

---

### Task 2.10c: Entity & Exclusion API

**Purpose:** Let the frontend fetch the database's schema tree and control which tables are accessible. This powers the entity tree checkboxes in the connection form — users check/uncheck tables to control what the AI agent (and query execution) can touch.

**Context:** The entity tree comes from DatabaseAdapter's `list_entities()` merged with ExclusionConfig (Task 2.3). Exclude/include endpoints update the config in ConfigStore. Note: the `/entities?include_columns=true` variant is also used by the Schema Browser (Phase 5) and the AI agent's `get_schema` tool (Phase 10).

**Files:**
- Modify: `local_backend/api/connections.py`
- Modify: `tests/local_backend/test_api_connections.py`

**What to implement:**
- `GET /connections/{id}/entities` — full entity tree with exclusion status. Supports `?include_columns=true` for Schema Browser
- `POST /connections/{id}/exclude` — mark entities as excluded
- `POST /connections/{id}/include` — mark entities as included
- `POST /connections/{id}/exclude-all` — block everything
- `POST /connections/{id}/include-all` — allow everything

**Tests (~10):** Fetch entities with mixed exclusion states, exclude/include operations, exclude-all/include-all, entity level validation per DB type, include_columns flag, 404 on missing connection

**Spec:** `docs/02-connection-management-backend-v2.md` → Section 5 (API Endpoints), entity/exclusion endpoints table

---

## Phase 3: Frontend — Connection Management

### Task 3.1: API Client Module

**Purpose:** Typed TypeScript client for all local backend and cloud backend HTTP calls. Every frontend component that talks to a backend goes through this module — it handles base URLs, request cancellation, and error normalization.

**Context:** The local backend runs at localhost:8765 (hardcoded for MVP). The cloud backend URL is configurable. AbortController support is critical — connection switch triggers cancellation of all in-flight requests. Error handling must detect "connection refused" (local backend not running) and surface it as a specific state so the UI can show install instructions.

**Files:**
- Create: `frontend/src/api/localBackend.ts`
- Create: `frontend/src/api/cloudBackend.ts`
- Create: `frontend/src/api/types.ts`

**What to implement:**
- Typed functions for all local backend endpoints (connections CRUD, test, activate, entities, exclude/include)
- Typed functions for cloud backend endpoints (sessions, messages, respond, cancel, SSE stream)
- Base URL configuration
- AbortController support for request cancellation
- Error handling: connection refused → `LocalBackendNotRunning` error type
- TypeScript types matching all API request/response schemas

**Tests (~6):** AbortController cancels in-flight request, error mapping for connection refused, correct URL construction, type-safe request/response

**Spec:** `docs/01-connection-management-frontend-v2.md` → Endpoints section (all 14 endpoints)

---

### Task 3.2: Connection Store (Zustand)

**Purpose:** Global state for connection management — which connections exist, which is active, loading states for async operations. Every component that needs connection info reads from this store.

**Context:** The store drives the Connection Panel (list of connections), the Connection Icon (active connection name + status dot), and coordinates the critical "connection switch" flow. When the user activates a different connection, this store calls `reset()` on every other store to clear stale data (schema, lineage, results, chat sessions). This is a project-wide rule — switching connections is a full reset.

**Files:**
- Create: `frontend/src/stores/connectionStore.ts`
- Create: `frontend/src/stores/__tests__/connectionStore.test.ts`

**What to implement:**
- State: connections list, activeConnectionId, loading states, isLocalBackendRunning
- Actions: fetchConnections, createConnection, updateConnection, deleteConnection, testConnection, activateConnection
- Connection switch = full reset: cancel all in-flight ops (AbortController), call reset() on all other stores
- Health check polling for local backend status

**Tests (~8):** Fetch populates list, create/update/delete modify list, activate sets active ID, connection switch resets dependent stores, health check updates isLocalBackendRunning

**Spec:** `docs/01-connection-management-frontend-v2.md` → Zustand Store section, Connection Switch behavior

---

### Task 3.3: Connection Icon & Panel

**Purpose:** The entry point for all connection management. The icon in the header shows the current connection status at a glance (green/red/gray dot + name), and clicking it opens a slide-out panel listing all saved connections with action buttons.

**Context:** The icon is always visible in the header — it's how users know they're connected and to which database. The panel shows connection cards with key info (name, type, host, entity counts) and actions (Edit, Test, Delete, Activate). An "Active" badge marks the current connection. Empty state prompts users to create their first connection.

**Files:**
- Create: `frontend/src/components/connections/ConnectionIcon.tsx`
- Create: `frontend/src/components/connections/ConnectionPanel.tsx`
- Create: `frontend/src/components/connections/ConnectionCard.tsx`
- Create: `frontend/src/components/connections/__tests__/`

**What to implement:**
- Connection icon in header (green/red/gray dot + name)
- Slide-out panel with connection cards
- Empty state ("Create your first connection"), active badge, action buttons (Edit, Test, Delete, Activate)

**Tests (4):** UI tests 1–4 from spec — icon states, panel open/close, card rendering, active badge

**Spec:** `docs/01-connection-management-frontend-v2.md` → UI Components 1–2 (Connection Icon, Connection Panel)

---

### Task 3.4: Connection Form Modal

**Purpose:** The form for creating and editing database connections. It dynamically shows different credential fields per DB type, lets users test connectivity before saving, and includes the entity exclusion tree for controlling AI access.

**Context:** The form has two modes: create (empty) and edit (prefilled, read-only by default — user must click Edit to unlock fields). The entity exclusion tree only appears after a successful connection test (since we need to query the DB to know what schemas/tables exist). The "Test Connection" button is the key UX moment — it validates credentials and populates the entity tree. An untested-save warning dialog prevents accidental saves with broken credentials.

**Files:**
- Create: `frontend/src/components/connections/ConnectionForm.tsx`
- Create: `frontend/src/components/connections/EntityTree.tsx`
- Create: `frontend/src/components/connections/__tests__/ConnectionForm.test.tsx`

**What to implement:**
- Connection form with dynamic fields per DB type (Postgres/MySQL: host, port, database, username, password; BigQuery: project_id, service_account_json)
- Test Connection button with spinner + latency display
- Entity exclusion tree: hierarchical checkboxes matching DB structure
- Include All / Exclude All buttons
- Search filter on entity tree
- Review section + Save button
- Edit mode (read-only by default, explicit Edit button)
- Untested save warning dialog

**Tests (25):** UI tests 5–29 from spec — dynamic fields per DB type, test connection flow, entity tree interactions, search filter, edit mode toggle, untested save warning

**Spec:** `docs/01-connection-management-frontend-v2.md` → UI Components 3–4 (Connection Form, Entity Tree)

---

### Task 3.5: Delete Confirmation & Local Backend Warning

**Purpose:** Safety dialogs — delete confirmation prevents accidental data loss, and the local backend warning helps users who haven't started the backend yet (or whose backend crashed).

**Context:** Delete confirmation names the connection being deleted so users can verify. The local backend warning appears when health check polling detects the backend is unreachable — it shows install/start instructions and a Retry button. The warning blocks all DB operations since nothing works without the local backend.

**Files:**
- Create: `frontend/src/components/connections/DeleteDialog.tsx`
- Create: `frontend/src/components/connections/LocalBackendWarning.tsx`

**What to implement:**
- Delete confirmation dialog with connection name
- Local backend not running warning with install instructions + Retry button
- Health check polling triggers warning show/hide

**Tests (7):** UI tests 30–36 from spec — delete dialog shows name, confirm deletes, cancel closes, warning appears when backend down, retry triggers health check

**Spec:** `docs/01-connection-management-frontend-v2.md` → UI Components 5–6 (Delete Dialog, Backend Warning)

---

## Phase 4: Local Backend — Schema & Query Endpoints

### Task 4.1: SQL Parser Service (sqlglot)

**Purpose:** Parse SQL into a lineage graph — the core data structure that powers the entire debugging experience. Every CTE, subquery, and table reference becomes a node with edges showing data flow. This is what the lineage visualization renders and what node execution operates on.

**Context:** sqlglot parses SQL into an AST, and this service walks the AST to extract nodes (CTEs, subqueries, table sources), edges (dependencies), source positions (for editor highlighting), and per-node SQL (for node execution). Node IDs have no type prefix: CTEs use their name, tables use qualified names, subqueries use parent_alias. The parser handles complex cases: self-joins (same table appearing twice), UNION branches, recursive CTEs, and subqueries in WHERE clauses. Results are cached in memory keyed by SQL text — the `execute-node` endpoint relies on this cache.

**Files:**
- Create: `local_backend/services/parser_service.py`
- Create: `tests/local_backend/test_parser_service.py`

**What to implement:**
- Parse SQL → lineage graph (nodes, edges, source_positions, node_sql)
- Node types: CTE, subquery, table_source
- Node ID format: CTE → name, table → qualified name (e.g., `public.orders`), subquery → parent_alias (e.g., `enriched_t1`)
- Dependency graph + precedence order
- Table name resolution per dialect (Postgres, MySQL, BigQuery)
- Handle: self-joins, UNION branches, recursive CTEs, subqueries in WHERE
- Parse cache in memory (keyed by SQL text)

**Tests (20):** Simple CTE, nested CTEs, subqueries with/without alias, table sources, multi-CTE, precedence order, invalid SQL, empty SQL, dialect-specific syntax, self-joins, UNION branches, recursive CTEs, dependency graph structure

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 2 (POST /query/parse), parse result schema

---

### Task 4.2: Query Execution Service

**Purpose:** Execute SQL queries with filter/order injection support. This is the engine behind the [Run] button, node execution from the lineage graph, and breakpoint execution. Injections let users add WHERE and ORDER BY clauses to specific nodes without modifying their original SQL.

**Context:** Injection works via sqlglot AST manipulation — WHERE clauses are appended with AND (or added if none exists), ORDER BY is appended to the node. For `execute-node`, the service uses the cached parse from Task 4.1 to find the target node, walks the dependency graph upward to collect ancestor nodes, reconstructs the minimal query needed, applies injections, and executes. Table sources get a simple `SELECT * FROM table LIMIT N` preview. Exclusion enforcement checks all table sources against the ExclusionConfig before executing. Request cancellation maps request_id to active DB cursors and kills them on cancel.

**Files:**
- Create: `local_backend/services/query_service.py`
- Create: `tests/local_backend/test_query_service.py`

**What to implement:**
- Execute full query with injections (AST manipulation via sqlglot)
- WHERE injection: append with AND (or add new WHERE)
- ORDER BY injection: append to node
- Result row limit (default 1000) + truncation flag
- Query timeout (default 60s)
- Request cancellation (request_id → active cursor map)
- Exclusion enforcement: reject if any table source is excluded

**Tests (8):** Simple query, WHERE injection, ORDER BY injection, both injections, result capped at limit, timeout exceeded, cancel mid-execution, connection not found

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 2 (POST /execute, POST /execute-node)

---

### Task 4.3: Execute-Node & Effective SQL

**Purpose:** Execute a single node's subtree (e.g., run just the "orders" CTE with its dependencies) and preview the full query with all injections applied without executing. Execute-node is the core debugging action — it lets users inspect intermediate results at any point in the query pipeline.

**Context:** Execute-node uses the cached parse to find the target node, then walks the dependency graph upward to collect all ancestor CTEs needed to run it. It reconstructs a minimal query (only the required CTEs + the target node), applies any active injections to each node, and executes. Effective SQL uses the same injection logic but returns the modified SQL text instead of executing — users see exactly what will run via the "View effective SQL" button.

**Files:**
- Modify: `local_backend/services/query_service.py`
- Create: `tests/local_backend/test_execute_node.py`
- Create: `tests/local_backend/test_effective_sql.py`

**What to implement:**
- Execute-node: find target node in cached parse, collect ancestor dependencies, reconstruct subtree query, apply injections, execute
- Table source execution: `SELECT * FROM schema.table LIMIT N`
- Effective SQL: build full query with all injections applied, return SQL text without executing
- Error: 400 if no cached parse or node_id not found

**Tests (17):** Execute-node: single CTE, CTE with upstream deps, injections on target/upstream/multiple nodes, table source execution, node not found, no cached parse (12 tests). Effective SQL: no injections, single, multiple, invalid injection, empty injections (5 tests)

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 2 (POST /execute-node, POST /effective-sql)

---

### Task 4.4: Query API Endpoints

**Purpose:** Expose parse, execute, execute-node, effective-sql, and cancel as HTTP endpoints. This is the FastAPI routing layer for all query operations — the frontend calls these for every query action.

**Context:** Thin layer over the parser service (Task 4.1) and query service (Tasks 4.2–4.3). The parse endpoint is called on every background re-parse (300ms debounce after typing). Execute and execute-node are called from the [Run] button, lineage node actions, and breakpoints. Cancel kills a running query by request_id.

**Files:**
- Create: `local_backend/api/query.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_query.py`

**What to implement:**
- `POST /query/parse` — parse SQL, cache result
- `POST /connections/{id}/execute` — execute with injections
- `POST /connections/{id}/execute-node` — execute node subtree (uses cached parse)
- `POST /query/effective-sql` — return modified SQL without executing
- `POST /connections/{id}/cancel` — cancel running query by request_id

**Tests (3+):** Cancel running query, unknown request_id, cancel already-completed query, plus integration tests for endpoint routing

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 2 (all 5 endpoints)

---

## Phase 5: Frontend — Schema Browser

### Task 5.1: Schema Store & Cache

**Purpose:** Manage the schema data lifecycle — fetch from backend, cache in localStorage, and serve stale data immediately while refreshing in the background. Users see their schema tree instantly on return visits instead of waiting for a DB round-trip.

**Context:** Schema cache uses stale-while-revalidate: show cached tree immediately, fetch fresh data in background, diff + merge without visual flash. Cache is per-connection (`schema_cache_{connection_id}` in localStorage). Cache invalidation happens on: connection delete, manual refresh, DDL detected after query execution, exclusion change. The `GET /connections/{id}/entities?include_columns=true` endpoint (implemented in Task 2.10c) provides both the tree structure and column types.

**Files:**
- Create: `frontend/src/stores/schemaStore.ts`
- Create: `frontend/src/stores/__tests__/schemaStore.test.ts`

**What to implement:**
- Zustand store: schema tree, loading state, error state, isRefreshing flag
- localStorage cache: `schema_cache_{connection_id}` with timestamp
- Stale-while-revalidate: show cache immediately, fetch in background, merge without flash
- Cache invalidation on connection delete, manual refresh, DDL detected, exclusion change
- `reset()` method for connection switch

**Tests (~8):** Cache hit returns immediately, background fetch updates store, cache miss shows loading, invalidation clears cache, reset clears everything, merge doesn't flash

**Spec:** `docs/03-schema-browser-frontend.md` → Data Flow section, Cache Details table

---

### Task 5.2a: Schema Tree Rendering

**Purpose:** Build the core tree component that displays the database structure. This is what users see when they open the Schema Browser — a navigable hierarchy of schemas/tables/columns that visually indicates which entities are excluded from AI debugging.

**Context:** The tree data comes from the schemaStore (Task 5.1). The hierarchy varies by DB type: Postgres (schema→table→column), MySQL (database→table→column), BigQuery (dataset→table→column). Excluded entities are still shown (greyed out with a special icon) — exclusion only affects AI access, not browsing. Column types are displayed right-aligned in muted monospace and can be long (e.g., BigQuery's `TIMESTAMP`), so they truncate with tooltip and are resizable.

**Files:**
- Create: `frontend/src/components/schema/SchemaBrowser.tsx`
- Create: `frontend/src/components/schema/SchemaTree.tsx`
- Create: `frontend/src/components/schema/SchemaNode.tsx`
- Create: `frontend/src/components/schema/__tests__/`

**What to implement:**
- Toggle button in toolbar (opens/closes panel, closed by default)
- Tree with expand/collapse per node
- Correct hierarchy per DB type
- Column types right-aligned, muted monospace, truncated with tooltip, resizable width
- Excluded entities: grey text + prohibited icon + tooltip ("Excluded from AI debugging" / "Excluded — inherited from [parent]")

**Tests (~18):** Tests 1–3 (toggle), 7–15 (hierarchy per DB type, column types, exclusion display), 38–40 (search in excluded parent, type truncation, column resize)

**Spec:** `docs/03-schema-browser-frontend.md` → UI Components sections 1–2 (Toggle, Panel), Column type display

---

### Task 5.2b: Panel States, Search & Footer

**Purpose:** Handle all the states the Schema Browser can be in and add the search filter + summary footer. Users need clear feedback about what's happening — especially the difference between "loading for the first time" (skeleton) and "refreshing in the background" (cached tree + subtle indicator).

**Context:** States depend on schemaStore flags (Task 5.1). The search filter is client-side — it filters the already-fetched tree by schema and table names (not columns), case-insensitive. The summary footer shows "X tables (Y excluded)" so users know their entity counts at a glance.

**Files:**
- Modify: `frontend/src/components/schema/SchemaBrowser.tsx`
- Modify: `frontend/src/components/schema/__tests__/`

**What to implement:**
- All 5 panel states: no connection, loading skeleton, cached+refreshing, error+retry, empty (0 tables)
- Search input with case-insensitive filtering on schema/table names
- Summary footer with table/exclusion counts
- Refresh button triggers foreground fetch
- Debounce: rapid refresh clicks don't fire duplicate requests

**Tests (~14):** Tests 4–6 (states), 16–25 (search, refresh, error, empty, footer), 41 (rapid clicks)

**Spec:** `docs/03-schema-browser-frontend.md` → UI Components section 3 (States), Search interactions

---

### Task 5.2c: Cache & Refresh Integration

**Purpose:** Wire up all the automatic refresh triggers so the schema stays fresh without manual intervention. This is the "stale-while-revalidate" behavior — users see cached data instantly while fresh data loads in the background.

**Context:** The schemaStore (Task 5.1) manages the cache, but this task wires up the triggers that cause refreshes. Connection switch must cancel in-flight fetches (AbortController) and load the new connection's cache. DDL detection is free because sqlglot already parses queries for lineage — if the statement is CREATE/ALTER/DROP, trigger a schema refresh after execution completes.

**Files:**
- Modify: `frontend/src/stores/schemaStore.ts`
- Modify: `frontend/src/components/schema/__tests__/`

**What to implement:**
- Auto-refresh on: connection select, page load with active connection, DDL detected after query execution, exclusion change
- Connection switch: cancel in-flight fetch, clear old cache, load new
- Background refresh updates tree without flash (diff + merge)

**Tests (~13):** Tests 26–37 (cache in localStorage, all refresh triggers, connection switch cancellation, exclusion change refresh), 42–45 (DB adapter schema fetch with include_columns)

**Spec:** `docs/03-schema-browser-frontend.md` → Data Flow section, Refresh Triggers Summary table

---

## Phase 6: Frontend — Query Console

### Task 6.1a: SQL Editor Core (CodeMirror 6)

**Purpose:** The main code editor where users write and paste SQL. This is the central workspace — all debugging starts here. CodeMirror 6 provides syntax highlighting, and background re-parsing keeps the lineage data current as the user types.

**Context:** The editor always shows the original SQL as the user wrote it — injections (filters/ordering) never appear in the editor. Background re-parse fires 300ms after the user stops typing (debounced) and silently updates source positions and dependency graph. The visual lineage graph only updates on explicit [Visualize] click, so the graph stays stable while the user edits. If re-parse fails (invalid SQL mid-edit), the system uses last known good positions and disables node execution with an error message.

**Files:**
- Create: `frontend/src/components/editor/SqlEditor.tsx`
- Create: `frontend/src/components/editor/__tests__/`

**What to implement:**
- CodeMirror 6 with SQL syntax highlighting (dialect-aware)
- Background re-parse: 300ms debounce after typing stops, calls `/query/parse`
- Paste SQL and upload .sql file support
- Failure handling: use last known good parse, disable node execution
- Right-click context menu: Execute, Add filter, Show in lineage

**Tests (~6):** Tests from spec — paste SQL, upload .sql file, syntax highlighting renders, background re-parse timing, re-parse failure handling, context menu appears

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 3 (SQL Editor), Section 7 (Background Re-parse)

---

### Task 6.1b: Gutter Buttons & Inline Execution

**Purpose:** Let users execute individual nodes (CTEs, subqueries, table sources) directly from the editor without going through the lineage graph. Hovering over a recognized SQL span shows a run button in the gutter — click it to see that node's results immediately.

**Context:** Gutter buttons only appear after the first successful parse (so the system knows which spans map to nodes). When hovering a recognized span, the full node extent gets a subtle background highlight and a play button appears in the gutter. For overlapping spans (e.g., a CTE containing a subquery), the innermost node takes priority; right-click shows all enclosing options. Clicking the play button triggers `execute-node` with active injections and opens the result in the Results Viewer.

**Files:**
- Create: `frontend/src/components/editor/gutterButtons.ts`
- Modify: `frontend/src/components/editor/SqlEditor.tsx`
- Modify: `frontend/src/components/editor/__tests__/`

**What to implement:**
- Hover recognized span → subtle background highlight + gutter play button
- Click play button → execute-node with active injections → result in Results Viewer
- Overlapping spans: innermost node priority, right-click for enclosing nodes
- No gutter buttons before first successful parse

**Tests (~12):** Tests from spec — hover CTE/subquery/table shows highlight + button, click executes node, table source → preview query, overlapping spans, no buttons before parse, right-click context menu, execute → result tab opens

**Spec:** `docs/05-query-console-lineage-detailed.md` → Sections 7 (Inline Execution), 8 (Gutter Buttons)

---

### Task 6.2: Action Bar & File Upload

**Purpose:** The toolbar above the editor with the main action buttons — Visualize (parse + show lineage), Run (execute full query), Upload .sql, and Cancel. These are the primary user actions that drive the whole debugging workflow.

**Context:** [Visualize] calls `/query/parse` and updates the lineage graph (unlike background re-parse, which only updates data silently). [Run] executes the full query with all active injections and opens results in the bottom panel. [Cancel] kills all active executions by request_id. [Run] is disabled when there's no active connection. All buttons show spinners and disable during operations.

**Files:**
- Create: `frontend/src/components/editor/ActionBar.tsx`
- Create: `frontend/src/components/editor/__tests__/ActionBar.test.tsx`

**What to implement:**
- [Visualize] button → calls parse, opens lineage tab, updates visual graph
- [Run] button → calls execute with SQL + injections, opens results tab. Disabled when no active connection
- [Upload .sql] → file picker, replaces editor content
- [Cancel] → visible during execution, cancels all active request_ids
- All buttons disabled + spinner during operations

**Tests (7):** Visualize calls parse + opens lineage, Run calls execute + opens results, Run disabled without connection, Upload opens file picker, Cancel visible/hidden, buttons disabled during ops, spinner shown

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 3 (Action Bar)

---

### Task 6.3: Parse & Execution Stores

**Purpose:** Global state for parse results and query execution — these stores connect the editor, lineage graph, and results viewer. The parse store tracks both background re-parses (silent) and explicit visualizations (graph updates), while the execution store tracks all running queries and their results.

**Context:** The parse store has two parse results: `parseResult` (updated silently on background re-parse, used for source positions and node execution) and `visualGraph` (updated only on explicit [Visualize], used to render the lineage graph). An `isGraphStale` flag shows when the editor content has changed since the last visualization. The execution store maps request_ids to results and tracks active executions for the cancel button.

**Files:**
- Create: `frontend/src/stores/parseStore.ts`
- Create: `frontend/src/stores/executionStore.ts`
- Create: `frontend/src/stores/__tests__/parseStore.test.ts`
- Create: `frontend/src/stores/__tests__/executionStore.test.ts`

**What to implement:**
- Parse store: `parseResult` (background), `visualGraph` (explicit Visualize), `isGraphStale` flag
- Execution store: `executionResults` map (request_id → result), `activeExecutions` map, `activeResultTab`
- Request ID generation, cancellation tracking
- `reset()` methods for connection switch

**Tests (~8):** Background parse updates parseResult but not visualGraph, Visualize updates both, isGraphStale set on edit + cleared on Visualize, execution result stored by request_id, cancel removes from active, reset clears everything

**Spec:** `docs/05-query-console-lineage-detailed.md` → Key State section

---

## Phase 7: Frontend — Lineage Visualization

### Task 7.1: React Flow + ELK Layout

**Purpose:** Render the lineage graph as an interactive node-and-edge diagram. React Flow provides the canvas with zoom/pan, and ELK (Eclipse Layout Kernel) automatically positions nodes so the graph is readable — sources at top, data flows down.

**Context:** The graph data comes from the parse store's `visualGraph` (Task 6.3). This task converts the parse result (nodes + edges) into React Flow format and runs ELK layout to position them. Two layout modes: Dependency (DAG showing data flow, default) and Precedence (nodes ordered by position in SQL). Standard graph interactions: zoom with scroll wheel, pan with click+drag.

**Files:**
- Create: `frontend/src/components/lineage/LineageGraph.tsx`
- Create: `frontend/src/components/lineage/elkLayout.ts`
- Create: `frontend/src/components/lineage/__tests__/`

**What to implement:**
- React Flow canvas with ELK layout engine
- Convert parse result (nodes + edges) to React Flow format
- Dependency graph layout (sources at top, data flows down)
- Precedence graph layout (narrative order, matching SQL position)
- Zoom, pan, standard graph interaction

**Tests (~5):** Graph renders correct number of nodes/edges, dependency mode has correct root nodes, precedence mode matches SQL order, zoom/pan work, empty graph renders cleanly

**Spec:** `docs/05-query-console-lineage-detailed.md` → Sections 4 (Lineage Graph), 5 (Graph Modes)

---

### Task 7.2: Lineage Nodes

**Purpose:** The visual design and interaction behavior of each node in the lineage graph. Nodes are color-coded by type (CTE=blue, Subquery=purple, Table=green), show execution status, and support click/double-click/right-click actions that connect to the editor and results viewer.

**Context:** Each node shows: a status indicator (idle/breakpointed/success/failed/executing), the node name, a quick-execute button, and a filter indicator when injections are active. Click selects the node and highlights its SQL span in the editor (bidirectional sync). Double-click executes immediately. Right-click opens a context menu with execute, breakpoint, filter, collapse, and show-in-editor actions. Hover highlights the node + direct edges.

**Files:**
- Create: `frontend/src/components/lineage/LineageNode.tsx`
- Create: `frontend/src/components/lineage/nodeStyles.ts`

**What to implement:**
- Color-coded nodes: Blue=CTE, Purple=Subquery, Green=Table
- Node content: status indicator, name, quick execute button, filter indicator
- Hover: highlight node + direct edges, tooltip with type label
- Click: select node, highlight SQL span in editor (bidirectional sync)
- Double-click: execute node with active injections
- Right-click: context menu (execute, breakpoint, filter, collapse, show in editor)
- Collapsed subtree: [+N] badge

**Tests (18):** Graph renders nodes/edges, dependency/precedence modes, mode toggle, click → highlights SQL, double-click → executes, right-click → context menu, collapse/expand, color-coding by type, type label on hover, hover highlights edges

**Spec:** `docs/05-query-console-lineage-detailed.md` → Sections 4 (Node Design), 5 (Interactions)

---

### Task 7.3: Lineage Toolbar & Graph Modes

**Purpose:** Controls above the lineage graph — mode toggle (Dependency/Precedence), breakpoint type filters, bulk actions (Run/Clear Breakpoints, Expand/Collapse All), and the staleness banner that tells users the graph is outdated.

**Context:** The toolbar appears above the React Flow canvas. The mode toggle switches between dependency view (data flow) and precedence view (SQL order). Breakpoint type filters (CTEs/Tables/Subqueries) only appear when breakpoints are set — they let users quickly toggle off/on breakpoints by node type. The staleness banner appears when the editor content has changed since the last [Visualize] click.

**Files:**
- Create: `frontend/src/components/lineage/LineageToolbar.tsx`

**What to implement:**
- Graph mode toggle (Dependency / Precedence)
- Breakpoint type filter (CTEs / Tables / Subqueries) — only visible when breakpoints set
- [Run Breakpoints] [Clear Breakpoints] buttons
- [Expand All] [Collapse All] buttons
- Staleness banner: "Graph outdated — click Visualize to refresh"

**Tests (~5):** Mode toggle switches layout, type filter toggles breakpoints, expand/collapse all works, staleness banner appears on edit + hides on Visualize, breakpoint controls hidden when no breakpoints

**Spec:** `docs/05-query-console-lineage-detailed.md` → Sections 5 (Graph Modes), 6 (Toolbar)

---

### Task 7.4: Breakpoints

**Purpose:** Let users mark nodes as "breakpoints" and execute them all in parallel — like setting breakpoints in a debugger but for SQL pipeline stages. This is the power feature for debugging complex queries: set breakpoints on key CTEs, run them all at once, and step through results.

**Context:** Breakpoints can be set on individual nodes, upstream subtrees (all ancestors), or downstream subtrees (all dependents). Type filters let users quickly toggle breakpoints by node type. "Run Breakpoints" executes all breakpointed nodes in parallel (separate `/execute-node` calls), waits for all to complete, then presents results one at a time with [Next] / [Show All] navigation. Tab order matches the current graph mode (dependency or precedence order).

**Files:**
- Create: `frontend/src/stores/breakpointStore.ts`
- Create: `frontend/src/components/lineage/__tests__/breakpoints.test.tsx`

**What to implement:**
- Toggle breakpoint on node (click indicator or right-click menu)
- Breakpoint upstream (all ancestors) / downstream (all dependents)
- Type filter: toggle off/on by node type
- Run Breakpoints: parallel execute-node calls, wait for all
- Results navigation: first tab shown, [Next] advances, [Show All] reveals all
- Tab order matches graph mode
- Cancel: single button cancels all running breakpoint executions

**Tests (15):** Toggle breakpoint, upstream/downstream, type filter, run executes in parallel, wait for all, show first result, [Next]/[Show All], tab order matches mode, clear breakpoints, cancel during execution, status indicators update, each breakpoint gets own tab

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 6 (Breakpoints)

---

### Task 7.5: Bidirectional Sync

**Purpose:** Keep the editor and lineage graph in sync — click a node in the graph and the corresponding SQL highlights in the editor, or click a SQL span in the editor and the matching node highlights in the graph. This is how users navigate between visual and textual representations of the same query.

**Context:** Sync relies on source positions from the parse result. Background re-parse (300ms debounce) keeps positions accurate as the user edits. The visual graph uses positions from its own parse (which may be older if the user hasn't clicked Visualize), but editing still works because both the background parse and the visual graph share node IDs. If re-parse fails mid-edit, the system falls back to last known good positions.

**Files:**
- Create: `frontend/src/components/editor/highlightSync.ts`
- Create: `frontend/src/stores/syncStore.ts`

**What to implement:**
- Lineage → Console: click node → scroll to + highlight SQL span
- Console → Lineage: click/select SQL span → highlight matching lineage node
- Background re-parse keeps positions accurate
- Failure handling: use last known good positions when parse fails

**Tests (5):** Click node → SQL highlighted, click SQL → node highlighted, edit SQL → positions update → sync still accurate, re-parse failure → last good positions, deselect clears highlights

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 8 (Bidirectional Sync)

---

### Task 7.6: Graph Collapse & Focus

**Purpose:** Keep large graphs manageable. Three mechanisms: collapse subtrees to hide complexity, "Show in lineage" to focus on a specific node's neighborhood, and smart defaults that auto-collapse large graphs on first render.

**Context:** Collapsing a node hides its children and shows a [+N] badge with the count. "Show in lineage" (triggered from the editor's right-click menu) scrolls to the node, centers it, and dims everything outside its immediate neighborhood (1 level up, 1 level down) — click the background to un-dim. Smart default: graphs with 12 or fewer nodes are fully expanded; 13+ nodes get auto-collapsed to root + direct dependencies.

**Files:**
- Modify: `frontend/src/components/lineage/LineageGraph.tsx`
- Create: `frontend/src/stores/graphViewStore.ts`

**What to implement:**
- Collapsible subtrees: right-click → collapse, children hidden, [+N] badge
- "Show in lineage" from editor: scroll to node, dim distant nodes, click background to un-dim
- Smart default: 12 or fewer nodes fully expanded, 13+ auto-collapsed

**Tests (~5):** Collapse hides children + shows badge, expand reveals children, show-in-lineage dims distant nodes, background click un-dims, smart default auto-collapses large graphs

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 10 (Collapse & Focus)

---

## Phase 8: Frontend — Results Viewer & Injection

### Task 8.1: Results Viewer

**Purpose:** Display query results in a tabbed table interface. Each executed node gets its own tab, so users can compare results across different pipeline stages. This is where debugging insights happen — users see actual data and spot issues.

**Context:** Uses TanStack Table for column sort, filter, and virtualized rendering. Each tab is independent (own sort, filter, scroll position). Tab types: node name tabs (from execute-node) and "Full Query" tab (from [Run]). Results show row count, execution time, and truncation status. NULL values are visually distinct (muted italic grey). Long cell values truncate with click-to-expand. Export via [Copy CSV] / [Copy JSON].

**Files:**
- Create: `frontend/src/components/results/ResultsViewer.tsx`
- Create: `frontend/src/components/results/ResultTabBar.tsx`
- Create: `frontend/src/components/results/ResultTable.tsx`
- Create: `frontend/src/components/results/__tests__/`

**What to implement:**
- TanStack Table integration
- Tab management: node tabs + "Full Query" tab, each independent
- Per-tab: column sort (click header), column filter, row count, execution time
- Truncated results message ("Showing 1,000 rows (query returned more)")
- NULL display: muted italic grey
- Long cell values: truncated, click to expand
- [Copy CSV] [Copy JSON] export
- States: loading (spinner), success (table), error (message + [Copy Error]), cancelled, empty (0 rows)

**Tests (12):** Full query result displayed, node execution in named tab, breakpoint results in separate tabs, per-tab sort/filter, row count display, truncated message, NULL styled, long cells expand, CSV/JSON export, error display, empty result message

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 11 (Results Viewer)

---

### Task 8.2: Filter & Order Injection Panel

**Purpose:** Let users add WHERE and ORDER BY clauses to specific nodes without editing their SQL. This is the non-destructive debugging tool — users filter or sort intermediate results to isolate issues while keeping their original query intact.

**Context:** Injections are stored client-side in sessionStorage (keyed by connection ID) — they persist across page refresh but clear when the tab closes. Each injection is per-node: optional WHERE clause and/or ORDER BY clause. The injection status bar shows "N filters active" and a [View effective SQL] button that opens a modal showing the full query with all injections applied (calls `/query/effective-sql`). Stale entries (node IDs that no longer exist after re-parse) are silently dropped. No validation on the SQL fragments — errors surface on execute.

**Files:**
- Create: `frontend/src/components/injection/FilterOrderPanel.tsx`
- Create: `frontend/src/components/injection/InjectionStatusBar.tsx`
- Create: `frontend/src/stores/injectionStore.ts`
- Create: `frontend/src/components/injection/__tests__/`

**What to implement:**
- Injection store: Map<nodeId, {where?, order_by?}> persisted in sessionStorage
- Status bar: "N filters active" + [View effective SQL]
- Panel: table with Node | WHERE | ORDER BY | [x] columns
- Inline editing of WHERE and ORDER BY cells
- [+ Add filter] with node dropdown
- [Clear All] removes all injections
- [View effective SQL] modal (calls `/query/effective-sql`)
- Stale entries: silently drop if node ID no longer exists after re-parse

**Tests (9):** Status bar shows count, click toggles panel, right-click node → Add filter, edit WHERE/ORDER BY inline, remove single injection, Clear All, View effective SQL modal, filters persist in sessionStorage, stale entries dropped

**Spec:** `docs/05-query-console-lineage-detailed.md` → Section 9 (Filter & Order Panel)

---

## Phase 9: Local Backend — AI Support Endpoints

### Task 9.1: Table Profile Endpoint

**Purpose:** Return table shape and column statistics (row count, null counts, distinct counts, min/max) for any table. This powers the AI chat agent's `table_profile` tool — when a user asks "what does the orders table look like?", the agent calls this endpoint through the frontend proxy to get a data profile similar to pandas' `df.describe()`.

**Context:** The endpoint generates a single SQL query with COUNT(*), COUNT(DISTINCT col), MIN/MAX (for numeric/date types only), and null counts per column. Exclusion enforcement returns 403 if the table is excluded — the AI agent should never see data from restricted tables. This endpoint also serves the debug agent indirectly (via `get_schema` context).

**Files:**
- Create: `local_backend/api/ai_support.py`
- Modify: `local_backend/main.py` (register router)
- Create: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `GET /connections/{id}/tables/{table}/profile`
- Generates profiling query: COUNT(*), COUNT(DISTINCT col), MIN(col), MAX(col), NULL count per column
- Min/max only for numeric and date/timestamp types (null for text/boolean)
- Exclusion enforcement: reject excluded tables with 403

**Tests (2):** Profile returns stats for valid table, excluded table returns 403

**Spec:** `docs/02-connection-management-backend-v2.md` → AI Agent Support Endpoints (profile)

---

### Task 9.2: Indexes Endpoint

**Purpose:** Return index, primary key, and partitioning info for a table. This powers the AI chat agent's `get_indexes` tool — when a user asks about query performance, the agent checks what indexes exist to give informed optimization advice.

**Context:** Index queries differ significantly across DB types: Postgres uses `pg_constraint` + `pg_index`, MySQL uses `information_schema.key_column_usage`, BigQuery has no traditional indexes but returns partitioning + clustering info. Exclusion enforcement returns 403 on excluded tables.

**Files:**
- Modify: `local_backend/api/ai_support.py`
- Modify: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `GET /connections/{id}/tables/{table}/indexes`
- Postgres: query `pg_constraint`, `pg_index`
- MySQL: query `information_schema.key_column_usage`
- BigQuery: return partitioning + clustering info
- Exclusion enforcement: 403 on excluded tables

**Tests (2):** Indexes returns data for valid table, excluded table returns 403

**Spec:** `docs/02-connection-management-backend-v2.md` → AI Agent Support Endpoints (indexes)

---

### Task 9.3: Sample Endpoint

**Purpose:** Return sample rows from a table. This powers the AI chat agent's `sample_data` tool — when the agent needs to see actual data to answer a question, it requests a few rows. Capped at 10 rows for chat context efficiency.

**Context:** Simple `SELECT * FROM table LIMIT N` query. The cloud agent specifies the limit (capped at 10 for chat, 50 for debug). Exclusion enforcement returns 403 on excluded tables. The response format matches the execute endpoint (columns + rows + total_rows + truncated flag) for consistency.

**Files:**
- Modify: `local_backend/api/ai_support.py`
- Modify: `tests/local_backend/test_api_ai_support.py`

**What to implement:**
- `POST /connections/{id}/sample`
- `SELECT * FROM table LIMIT N`
- Exclusion enforcement: 403 on excluded tables

**Tests (2):** Sample returns rows for valid table, excluded table returns 403

**Spec:** `docs/02-connection-management-backend-v2.md` → AI Agent Support Endpoints (sample)

---

## Phase 10: Cloud Backend

### Task 10.1: Session Management

**Purpose:** Track AI chat and debug sessions — their lifecycle, state, context, and limits. Sessions are the container for all AI interactions: each chat tab and each debug investigation is a separate session.

**Context:** Sessions live in memory (Redis exit path for post-MVP). Lifecycle: Created → Active → (Waiting for tool result ↔ Active) → Completed/Cancelled/Error. Key constraint: only one debug session at a time (returns 409 if another is running). Sessions timeout after 30 minutes of inactivity. A background task cleans up expired sessions every 5 minutes. Each session stores the query context (query text, lineage, schema, DB type, excluded tables) sent by the frontend on creation.

**Files:**
- Create: `cloud_backend/sessions/session_store.py`
- Create: `cloud_backend/models/session.py`
- Create: `tests/cloud_backend/test_session_store.py`

**What to implement:**
- In-memory session map: `session_id → SessionState`
- Session creation (chat and debug types)
- Session lookup, status tracking (active, waiting_tool, completed, cancelled, error)
- One debug session at a time enforcement (409 if exists)
- Session timeout (30 min inactive) + background cleanup task
- Context storage: query_text, lineage, schema, db_type, excluded_tables
- Debug-specific context: bug_category, bug_details, hint
- Query count and LLM call count tracking

**Tests (9):** Create chat/debug sessions, second debug blocked (409), multiple chats allowed, cleanup after completion/cancel, timeout expiry, query/LLM count tracking

**Spec:** `docs/07-cloud-backend.md` → Section 4 (Session Management), session limits table

---

### Task 10.2: SSE Streaming & Event Registry

**Purpose:** Stream AI responses and tool requests to the frontend in real-time via Server-Sent Events. SSE is the communication channel for everything the AI agent does — progress updates, streamed text, tool call requests, and the final debug report.

**Context:** The SSE registry maps session_id → open SSE connection. Event types: `progress` (action summaries during debug), `tool_call` (agent needs frontend to call local backend), `chat_response` (streamed text chunks), `chat_response_end` (marks end of response), `conclusion` (debug report), `error`. Each event has a sequence number for reconnection — if the frontend disconnects and reconnects, the server replays missed events from the event log.

**Files:**
- Create: `cloud_backend/sessions/sse_registry.py`
- Create: `cloud_backend/models/events.py`
- Create: `cloud_backend/api/sessions.py`
- Create: `tests/cloud_backend/test_sse.py`

**What to implement:**
- SSE registry: `session_id → open SSE connection`
- Event types: progress, tool_call, chat_response, chat_response_end, conclusion, error
- `GET /sessions/{id}/stream` — SSE endpoint
- `POST /sessions/{id}/respond` — route tool result to waiting agent (by call_id)
- `POST /sessions/{id}/cancel` — cancel session
- Event log per session for reconnection replay
- Sequence numbers for missed event detection

**Tests (6):** SSE stream opens/rejects, /respond routes to correct session, wrong call_id returns 400, expired session returns 404, reconnect replays missed events

**Spec:** `docs/07-cloud-backend.md` → Sections 3 (SSE), 4 (Event Types)

---

### Task 10.3: Chat & Debug API Endpoints

**Purpose:** Create and manage chat and debug sessions via HTTP. These endpoints are what the frontend calls when a user starts a new chat, sends a message, or launches a debug investigation.

**Context:** Chat session creation receives the current query context (query text, lineage, schema, DB type, excluded tables) so the agent can answer questions about the user's query. Debug session creation additionally receives the bug category, details, and optional hint from the Debug Wizard. Messages trigger the LangGraph agent which processes asynchronously and streams responses via SSE.

**Files:**
- Create: `cloud_backend/api/chat.py`
- Create: `cloud_backend/api/debug.py`
- Modify: `cloud_backend/main.py` (register routers)
- Create: `tests/cloud_backend/test_api_chat.py`
- Create: `tests/cloud_backend/test_api_debug.py`

**What to implement:**
- `POST /chat/sessions` — create chat session with context (query, lineage, schema, db_type, excluded_tables)
- `POST /chat/{id}/message` — send message, triggers agent, returns 202 (response comes via SSE)
- `POST /debug/sessions` — create debug session with context + bug_category, bug_details, hint
- Context injection into LLM system prompt

**Tests (~5):** Create chat session returns session_id, create debug returns session_id, send message returns 202, debug with missing context returns 400, context stored in session

**Spec:** `docs/07-cloud-backend.md` → Section 3 (API Endpoints)

---

### Task 10.4a: Debug Agent Tools (Cloud-side)

**Purpose:** The 5 tools the debug agent uses to investigate SQL bugs. Each tool emits an SSE `tool_call` event, the frontend proxies the call to the local backend, and posts the result back. The cloud never talks to the local backend directly — credentials stay safe.

**Context:** The tool-call flow: (1) LangGraph agent decides to call a tool, (2) cloud emits `tool_call` SSE event with call_id + arguments, (3) frontend calls local backend, (4) frontend POSTs result to `/sessions/{id}/respond`, (5) agent resumes. Each tool enforces exclusion rules before emitting the tool_call: `validate_query` checks parsed nodes for excluded tables, `execute_query` validates first, `get_schema` filters excluded tables from the response, `get_node_results` rejects if any table in the subtree is excluded, `get_lineage` returns from session state (no endpoint call needed). Results are capped at 50 rows and 200 chars per cell to manage LLM context.

**Files:**
- Create: `cloud_backend/agents/tools/validate_query.py`
- Create: `cloud_backend/agents/tools/execute_query.py`
- Create: `cloud_backend/agents/tools/get_schema.py`
- Create: `cloud_backend/agents/tools/get_node_results.py`
- Create: `cloud_backend/agents/tools/get_lineage.py`
- Create: `tests/cloud_backend/test_debug_tools.py`

**What to implement:**
- Each tool emits a `tool_call` SSE event and waits for `/respond`
- `validate_query`: parse + exclusion check + SELECT-only. Reject SELECT *, return available columns
- `execute_query`: validate first, then execute. Results capped at 50 rows, cells truncated at 200 chars
- `get_schema`: filter out excluded tables from response before passing to LLM
- `get_node_results`: check subtree for excluded tables, reject if any excluded
- `get_lineage`: return from session state (no endpoint call)

**Tests (~8):** validate_query rejects SELECT */DDL/DML/excluded table + accepts valid SELECT, execute_query validates first, get_schema filters excluded, get_node_results rejects excluded subtree, results capped at 50 rows, cells truncated at 200 chars

**Spec:** `docs/07-cloud-backend.md` → Section 5 (Agent Tools), `docs/06-ai-chat-and-debugging.md` → Section 4.1 (Debug Tools)

---

### Task 10.4b: Chat Agent Tools (Cloud-side)

**Purpose:** The 3 tools the chat agent uses to look up data when answering questions. These are simpler than the debug tools — they fetch table metadata and sample rows for context.

**Context:** Same tool-call flow as debug tools (SSE → frontend → local backend → respond). `table_profile` returns row count, null counts, distinct counts, min/max (like `df.describe()`). `get_indexes` returns indexes, PKs, partitioning info. `sample_data` returns N sample rows (capped at 10 for chat). All reject excluded tables. Results are formatted as readable text before being passed to the LLM.

**Files:**
- Create: `cloud_backend/agents/tools/table_profile.py`
- Create: `cloud_backend/agents/tools/get_indexes.py`
- Create: `cloud_backend/agents/tools/sample_data.py`
- Create: `tests/cloud_backend/test_chat_tools.py`

**What to implement:**
- `table_profile`: emit tool_call, receive profile data, format for LLM. Reject excluded tables
- `get_indexes`: emit tool_call, receive index data, format for LLM. Reject excluded tables
- `sample_data`: emit tool_call, receive rows (capped at 10). Reject excluded tables

**Tests (~4):** table_profile/get_indexes/sample_data reject excluded tables, sample_data caps at 10 rows

**Spec:** `docs/07-cloud-backend.md` → Section 5 (Agent Tools), `docs/06-ai-chat-and-debugging.md` → Section 5.1 (Chat Tools)

---

### Task 10.5: Chat Agent (LangGraph)

**Purpose:** The AI assistant for free-form Q&A about SQL queries, schema, and data. Users ask questions in natural language and get streamed responses that seamlessly include data from tool calls without showing tool usage.

**Context:** Built as a LangGraph reactive agent (create_react_agent with tool nodes). The system prompt includes: role, current query context, available tools, allowed topics (query explanation, schema questions, general SQL, DB features, domain interpretation), blocked topics (DDL/DML generation, writing queries from scratch, non-SQL topics). When the user describes unexpected behavior, the agent suggests switching to Debug mode. Tool results appear inline in the response — no "I used a tool" indicators.

**Files:**
- Create: `cloud_backend/agents/chat_agent.py`
- Create: `tests/cloud_backend/test_chat_agent.py`

**What to implement:**
- LangGraph graph: generate response with tools → stream to frontend via SSE (chat_response events)
- System prompt: role, context, tools, allowed/blocked topics, DB dialect, soft redirect to debug mode
- Tools: table_profile, get_indexes, sample_data (from Task 10.4b)
- Streaming: chunk responses via SSE (chat_response + chat_response_end events)
- Tool results inline in response (no tool usage indicator)

**Tests (7):** Responds to query explanation, general SQL, DB features; blocks DDL/DML generation, blocks "write me a query", blocks non-SQL topics; suggests debug mode for unexpected behavior

**Spec:** `docs/06-ai-chat-and-debugging.md` → Sections 5 (Chat Agent), 8 (Guardrails)

---

### Task 10.6: Debug Agent (LangGraph)

**Purpose:** The automated SQL bug investigator. Given a bug report (category + description + hint), it systematically investigates the query by executing nodes, checking data, and producing a structured report with a verdict (query_bug / expected_behavior / potential_data_bug).

**Context:** Built as a LangGraph state machine with 4 nodes: `plan` (decide next investigation step), `execute` (call tools), `analyze` (interpret results, decide if more investigation needed), `report` (generate final report with verdict). The agent always starts from the final query output and traces backwards through the lineage. Session limits prevent runaway costs: max 15 queries, 3 retries on failed queries, 20 LLM calls. The system prompt enforces "NEVER use SELECT *" and "Use COUNT/GROUP BY before fetching raw rows" to manage context size. The report includes: conclusion (verdict + summary), ordered investigation steps (each with expandable evidence), observations (anomalies discovered), next steps, and limitations.

**Files:**
- Create: `cloud_backend/agents/debug_agent.py`
- Create: `tests/cloud_backend/test_debug_agent.py`

**What to implement:**
- LangGraph state machine: plan → execute → analyze → (loop or report)
- System prompt: role, context, investigation rules, verdicts, query rules (no SELECT *, use aggregation first), report format, limits
- Tools: validate_query, execute_query, get_schema, get_node_results, get_lineage (from Task 10.4a)
- Session limits: 15 queries, 3 retries, 20 LLM calls
- Verdicts: query_bug, expected_behavior, potential_data_bug
- Report structure: conclusion → investigation steps (with evidence) → observations → next steps → limitations
- Progress events emitted during investigation (progress SSE events)
- Cancel: stop agent, produce partial report if possible

**Tests (6):** Agent stops after max queries (partial report), retries invalid query up to 3 times, stops after max LLM calls, cancel stops agent, cancel returns partial report if possible, progress events emitted

**Spec:** `docs/06-ai-chat-and-debugging.md` → Sections 4 (Debug Agent), 8 (Guardrails), `docs/07-cloud-backend.md` → Section 6 (Agent Design)

---

## Phase 11: Frontend — AI Chat & Debug

### Task 11.1: SSE Client & Chat Store

**Purpose:** Handle real-time communication with the cloud backend and manage chat/debug session state. The SSE client receives streamed responses, tool call requests, progress updates, and debug reports — the chat store organizes this into sessions and messages.

**Context:** The SSE client connects to `GET /sessions/{id}/stream` and dispatches events by type. For `tool_call` events, it calls the local backend (using the API client from Task 3.1), then POSTs the result to `/sessions/{id}/respond` — this is the frontend-as-proxy pattern that keeps credentials safe. The chat store manages multiple sessions (tabs), each with its own message history, loading state, and SSE connection. Tab management: multiple chat tabs allowed, one debug at a time.

**Files:**
- Create: `frontend/src/api/sseClient.ts`
- Create: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/stores/__tests__/chatStore.test.ts`

**What to implement:**
- SSE client: connect to `/sessions/{id}/stream`, handle all event types, auto-reconnect on disconnect
- Chat store: sessions list, active session, messages per session, loading states
- Tab management: multiple chat tabs, one debug at a time
- Tool call handling: receive tool_call event → call local backend → POST /respond
- `reset()` method for connection switch (cancel debug, clear all sessions)

**Tests (~8):** SSE receives and dispatches events, tool_call triggers local backend call + respond, multiple sessions tracked independently, auto-reconnect on disconnect, reset clears everything

**Spec:** `docs/07-cloud-backend.md` → Section 3 (SSE Flow), `docs/06-ai-chat-and-debugging.md` → Section 6 (Chat Panel)

---

### Task 11.2: Chat Panel UI

**Purpose:** The right sidebar panel where users interact with the AI — ask questions about their query (Chat mode) or launch a debug investigation (Debug mode). Each tab is its own conversation with separate history and session.

**Context:** The panel is hidden by default, toggleable via a button. A mode dropdown at the top switches between Chat and Debug — mode is per-tab. The context indicator at the top shows what the agent "knows" (query loaded, CTE count, schema summary). Chat mode is a standard message interface with streamed responses. Inline data tables in responses use a 5x5 scrollable viewport to avoid blowing up the layout.

**Files:**
- Create: `frontend/src/components/chat/ChatPanel.tsx`
- Create: `frontend/src/components/chat/ChatTabs.tsx`
- Create: `frontend/src/components/chat/ChatMessage.tsx`
- Create: `frontend/src/components/chat/ContextIndicator.tsx`
- Create: `frontend/src/components/chat/__tests__/`

**What to implement:**
- Right sidebar panel, hidden by default, toggleable
- Mode dropdown: Chat / Debug (per-tab)
- Tab management: [+] button (New Chat / New Debug), tab switching, close tab
- Context indicator: query status, CTE count, schema summary
- Chat mode: message input, streamed response display, scrollable history
- Inline data tables in responses (5x5 scrollable viewport)

**Tests (13):** Tests 54–66 from spec — panel toggle, mode switching, tab management, context indicator, message send + streamed response, chat history, new chat empty history

**Spec:** `docs/06-ai-chat-and-debugging.md` → Section 6 (Chat Panel UI)

---

### Task 11.3: Debug Wizard

**Purpose:** The structured entry point for debug investigations. Instead of free-form "something is wrong", the wizard guides users through selecting a bug category, providing details, and optionally adding a hint — giving the debug agent a focused starting point.

**Context:** 5 bug categories: unexpected row count, unexpected nulls, unexpected values, missing columns, duplicate columns. Each category has specific follow-up questions (e.g., row count → too many/too few/no results). After the wizard, "Go" creates a debug session with the structured input and starts the investigation. The wizard blocks if no query is loaded, query has syntax errors, or all tables are excluded.

**Files:**
- Create: `frontend/src/components/chat/DebugWizard.tsx`
- Create: `frontend/src/components/chat/__tests__/DebugWizard.test.tsx`

**What to implement:**
- Step 1: Category selection (row count, nulls, values, missing columns, duplicate columns)
- Step 2: Category-specific follow-up (structured options + free text)
- Step 3: Hint (optional free text)
- Step 4: Go → creates debug session, starts investigation
- Blocked states: no query loaded, syntax errors, all tables excluded

**Tests (7):** Tests 67–73 from spec — category selection, sub-options shown, description field, hint optional, Go starts investigation, blocked without query, blocked with syntax errors

**Spec:** `docs/06-ai-chat-and-debugging.md` → Sections 4.2 (Debug Wizard), 6.6 (Wizard UI)

---

### Task 11.4: Debug Progress & Report

**Purpose:** Show what the debug agent is doing during investigation (progress) and display the final structured report with verdict, evidence, and next steps. This is the payoff of the whole product — the user sees a thorough investigation with supporting data.

**Context:** During investigation, action summaries appear one by one ("Checked enriched CTE for null prices", "Looked up product_ids in products table"). A sound notification plays when the report is ready, and a badge appears on the debug tab if it's not active. The report has structured sections: conclusion (verdict + summary), investigation steps (each with expandable evidence showing the SQL query and result table), observations marked with warning indicators, next steps, and limitations. Evidence tables use a 5x5 fixed viewport with scrolling. Back-references link steps that reuse the same query.

**Files:**
- Create: `frontend/src/components/chat/DebugProgress.tsx`
- Create: `frontend/src/components/chat/DebugReport.tsx`
- Create: `frontend/src/components/chat/__tests__/DebugReport.test.tsx`

**What to implement:**
- Progress: action summaries appearing one by one, "This may take a few minutes", Cancel button
- Sound notification on completion
- Badge indicator on debug tab when report ready and tab not active
- Report: verdict display (query_bug / expected_behavior / potential_data_bug), ordered investigation steps, expandable evidence (query + results table in 5x5 viewport), back-references ("see step 2"), observations with warning marker, next steps, limitations

**Tests (12):** Tests 74–85 from spec — progress summaries, cancel button, sound notification, verdict display, investigation steps ordered, expandable evidence, evidence table scrollable, back-reference links, observations marked, next steps shown, limitations shown

**Spec:** `docs/06-ai-chat-and-debugging.md` → Sections 4.5 (Progress), 4.8 (Report), 6 (Report UI)

---

### Task 11.5: Edge Cases & Connection Switch

**Purpose:** Handle all the things that can go wrong during AI interactions — connection switches mid-debug, query edits during investigation, SSE disconnects, LLM errors, and blocked states.

**Context:** Connection switch is the most complex case: cancel any active debug session, clear all chat sessions, show cancellation message. Query edited during debug shows a banner ("Query changed since debug started"). Second debug session is blocked with a message. SSE disconnect triggers auto-reconnect with event replay. LLM API errors retry once, then show an error message. All tables excluded blocks debug with a specific message.

**Files:**
- Modify: `frontend/src/stores/chatStore.ts`
- Create: `frontend/src/components/chat/__tests__/edgeCases.test.tsx`

**What to implement:**
- Connection switch: cancel debug, clear chat sessions, show cancellation message
- Query edited during debug: banner "Query changed since debug started"
- All tables excluded: block debug with message
- SSE disconnect: auto-reconnect with event replay
- LLM API error: retry once, then show error
- Second debug session: blocked with message

**Tests (8):** Tests 86–93 from spec — connection switch cancels debug, cancellation message shown, chat cleared, second debug blocked, query edited banner, all tables excluded, SSE reconnect, LLM error retry

**Spec:** `docs/06-ai-chat-and-debugging.md` → Section 9 (Edge Cases)

---

## Phase 12: Integration & Polish

### Task 12.1: Connection Switch Full Reset

**Purpose:** Ensure switching the active connection is a clean slate — no stale data from the previous connection leaks into the new one. This is a project-wide rule that touches every store.

**Context:** When the user activates a different connection, every piece of state tied to the old connection must be cleared: schema cache, lineage graph, parse cache, results tabs, injections, chat/debug sessions. Each store exposes a `reset()` method (implemented in earlier tasks), and the connectionStore calls them all on switch. AbortController cancels all in-flight requests so no stale responses arrive after the switch.

**Files:**
- Modify: `frontend/src/stores/connectionStore.ts`
- Modify: all other stores (verify reset() methods)

**What to implement:**
- When active connection changes: AbortController cancels all in-flight requests
- Clear: schema cache, lineage graph, parse cache, results tabs, injections, chat/debug sessions
- Each store's `reset()` method called from connectionStore on switch
- Verify no stale data leaks after switch

**Spec:** `docs/project-overview.md` → Project-wide Rules (Connection Switch)

---

### Task 12.2: End-to-End Flow Tests

**Purpose:** Verify the full user journey works end-to-end — from creating a connection through debugging a query and getting a report. These tests catch integration issues that unit tests miss.

**Context:** Three main flows: (1) happy path — create connection → test → save → activate → browse schema → paste query → visualize → execute node → add filter → run debug → get report, (2) connection switch mid-flow — verify full reset, (3) error flows — local backend down, cloud backend down, DB unreachable.

**Files:**
- Create: `tests/e2e/test_connection_flow.py`
- Create: `tests/e2e/test_query_debug_flow.py`

**What to implement:**
- Full happy-path flow
- Connection switch mid-flow: verify full reset
- Error flows: local backend down, cloud backend down, DB unreachable

**Spec:** All spec documents (cross-cutting)

---

### Task 12.3: Docker Compose Production

**Purpose:** Production-ready deployment configuration. The cloud backend and frontend deploy to Railway/Render, while the local backend runs on the user's machine via pip install.

**Context:** Production differs from dev: frontend is built and served statically (from cloud backend or CDN), CORS is configured for the cloud frontend origin to reach the local backend at localhost:8765, and environment variables are configured for the hosting platform.

**Files:**
- Modify: `docker-compose.yml`
- Create: `docker-compose.prod.yml`

**What to implement:**
- Production compose: frontend served from cloud backend (or separate CDN)
- CORS configuration: cloud frontend origin → local backend
- Environment variable configuration for Railway/Render

**Spec:** `docs/project-overview.md` → Deployment section

---

## Summary

| Phase | Tasks | Est. Tests |
|-------|-------|-----------|
| 1. Scaffolding | 4 | ~10 |
| 2. Local Backend — Connections | 12 | ~132 |
| 3. Frontend — Connections | 5 | ~50 |
| 4. Local Backend — Schema & Query | 4 | ~48 |
| 5. Frontend — Schema Browser | 4 | ~53 |
| 6. Frontend — Query Console | 4 | ~33 |
| 7. Frontend — Lineage | 6 | ~53 |
| 8. Frontend — Results & Injection | 2 | ~21 |
| 9. Local Backend — AI Endpoints | 3 | ~6 |
| 10. Cloud Backend | 7 | ~45 |
| 11. Frontend — AI Chat & Debug | 5 | ~48 |
| 12. Integration & Polish | 3 | ~10 |
| **Total** | **59 tasks** | **~509 tests** |
