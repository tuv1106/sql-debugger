# SQL Debugger — Connection Management Frontend Spec

**Version:** 2.0
**Date:** February 2026
**Status:** Approved for MVP
**Changelog:** v2.0 — Hierarchical entity exclusion (replaces flat table blocking)

---

## Table of Contents

1. [Product Context](#product-context)
2. [Feature Description](#feature-description)
3. [Scope](#scope)
4. [Architecture](#architecture)
5. [UI Components](#ui-components)
6. [Endpoints](#endpoints)
7. [Error Handling](#error-handling)
8. [Tests](#tests)
9. [Decisions Log](#decisions-log)

---

## Product Context

### Product Vision

An AI-powered SQL debugging tool for analysts and data engineers. Combines query visualization, interactive execution, and agentic root-cause analysis to help users find bugs in complex queries.

### Target Users

- Analysts
- Data engineers

### Differentiator

Nobody offers visual lineage + click-to-execute + AI-driven debugging in one tool.

### MVP Features (Full List)

| Feature | In MVP |
|---------|--------|
| Query Lineage Visualization | ✅ |
| Click Node → Execute | ✅ |
| Filter & Order Injection | ✅ |
| Results Viewer (with client-side sort/filter) | ✅ |
| Agentic Debugging (within query) | ✅ |
| Free Chat (query-aware) | ✅ |
| Query Console (paste, upload, edit, run) | ✅ |
| Schema Browser (simple tree) | ✅ |
| Connection Management | ✅ (this spec) |
| Query Optimization Suggestions | ❌ |
| Cross-query Debugging | ❌ |
| Column-level Lineage | ❌ |
| Aggregation Views / Data Profiling | ❌ |

### Database Support

| Database | MVP |
|----------|-----|
| Postgres | ✅ |
| MySQL | ✅ |
| BigQuery | ✅ |
| Snowflake | ✅ |

---

## Feature Description

### Goal

Allow users to securely connect their database to the tool.

### What It Solves

- Users need to authenticate to their DB before any functionality works
- Credentials must stay on user's machine (security requirement)
- Users need control over which entities (schemas, datasets, tables) the AI agent can access
- Users need multiple saved connections (prod, staging, dev, etc.)

### User Flow

1. User installs local backend (`pip install sql-debugger`)
2. User runs local backend (`sql-debugger start`)
3. User opens web UI in browser
4. Web UI detects local backend (or prompts to start it)
5. User creates connection with name, type, credentials
6. User tests connection
7. User configures entity access (exclude schemas/datasets/tables from debugging)
8. User saves connection
9. User activates connection to use it
10. User can switch between saved connections

---

## Scope

### In MVP

- Support Postgres, MySQL, BigQuery, Snowflake
- Multiple saved connections
- One active connection at a time
- Connection naming (user-defined)
- Basic auth:
  - Postgres/MySQL: host, port, database, username, password
  - BigQuery: project ID, dataset, service account JSON
  - Snowflake: account, warehouse, database, schema, username, password
- Hierarchical entity exclusion (schema/dataset/database/table level)
- Allow All / Exclude All buttons
- Connection test with latency display
- Warning if saving without testing changes
- Credentials stored in OS keyring (with encrypted file fallback)
- Multiple browser tabs allowed (stateless design)

### Out of MVP

- SSH tunneling
- OAuth flows
- Connection pooling
- Connection sharing between users
- Team/shared connections

---

## Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│                         BROWSER                             │
│                                                             │
│   UI JavaScript runs here                                   │
│   (loaded from Railway/Render, but EXECUTES in browser)    │
│                                                             │
│         │                              │                    │
│         │ fetch("localhost:8765/...")  │ fetch("api.yourapp.com/...")
│         │ (DB operations)              │ (LLM agent calls)  │
│         ▼                              ▼                    │
└─────────┼──────────────────────────────┼────────────────────┘
          │                              │
          ▼                              ▼
   ┌──────────────┐              ┌──────────────┐
   │Local Backend │              │    Cloud     │
   │ (user's PC)  │              │  (Railway)   │
   │              │              │              │
   │ - DB creds   │              │ - LLM/Agent  │
   │ - Query exec │              │ - No DB data │
   └──────┬───────┘              └──────────────┘
          │
          ▼
   ┌──────────────┐
   │   User's DB  │
   │  (RDS, etc)  │
   └──────────────┘
```

### Key Security Properties

- **Credentials never leave user's machine** — stored in OS keyring
- **Query results never touch cloud** — go directly from local backend to browser
- **Cloud only sees:** query text (for agent reasoning), schema metadata (if user allows)
- **No auth needed between local backend and cloud** — they don't communicate directly

### Terminology

| Term | Meaning |
|------|---------|
| Local Backend | Python server on user's machine, handles DB operations |
| Cloud Backend | Railway/Render server, handles LLM/analysis |
| Agent | AI agent for debugging (uses LLM) |
| Excluded Entity | Schema, dataset, database, or table excluded from AI debugging context |

---

## Entity Exclusion Model

### Concept

"Excluded" means excluded from AI debugging context. Users can still browse, preview, and query excluded entities. Data from excluded entities is never sent to the LLM/agent.

### Excludable Levels Per DB Type

| DB | Excludable Levels | Not Excludable (= the connection itself) |
|----|-------------------|------------------------------------------|
| Postgres | schema, table | database |
| MySQL | database, table | — |
| BigQuery | dataset, table | project |
| Snowflake | database, schema, table | — |

### Storage (Denormalized)

Exclusions stored redundantly for fast reads. Example (Postgres):

```json
{
  "blocked_schemas": ["sensitive", "pii"],
  "blocked_tables": {
    "sensitive": ["users", "payments", "audit_log"],
    "pii": ["customers", "addresses"],
    "public": ["internal_config"]
  }
}
```

### Operations

| Action | Storage Change |
|--------|----------------|
| Exclude schema X | Add X to `blocked_schemas`. Add ALL current tables under X to `blocked_tables[X]` |
| Include table X.foo (X is excluded) | Remove foo from `blocked_tables[X]`. Remove X from `blocked_schemas` |
| Include schema X | Remove X from `blocked_schemas`. Remove `blocked_tables[X]` entirely |
| Exclude table X.foo | Add foo to `blocked_tables[X]`. Do NOT auto-promote schema |
| Exclude All | Add all top-level entities to blocked list. Add all tables to `blocked_tables` |
| Include All | Clear all blocked lists |

### Key Rules

- `blocked_schemas` only contains schemas the user **explicitly** excluded at schema level
- No auto-promotion: if all tables in a schema happen to be individually excluded, the schema is NOT added to `blocked_schemas`
- New table in explicitly-excluded schema → automatically excluded (inherited)
- New table in schema where all tables individually excluded → **NOT excluded** (user never excluded the schema)
- On schema refresh: new tables in excluded schemas are auto-added to `blocked_tables` for sync

### View Warning

> "Views that reference excluded tables are not automatically detected. Debugging results from such views is your responsibility."

Displayed once in the entity access UI section.

---

## UI Components

### 1. Connection Icon (Header)

Location: Top-right area of main header

```
┌─────────────────────────────────────────────────────────────┐
│  SQL Debugger          🔌 Production MySQL ▼     [user]     │
└─────────────────────────────────────────────────────────────┘
```

**States:**
- 🟢 Green dot = connected (active connection)
- 🔴 Red dot = disconnected / error
- ⚪ Gray = no connection configured

**Behavior:**
- Shows active connection name
- Click opens Connection Panel

---

### 2. Connection Panel (Slide-out or Modal)

```
┌─────────────────────────────────────────────────────────────┐
│  Connections                                    [+ New]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ 🟢 Production MySQL                    [Active]       │  │
│  │    mysql • prod-db.rds.amazonaws.com                  │  │
│  │    47 tables allowed, 3 excluded from debugging       │  │
│  │                                                       │  │
│  │              [Edit]  [Test]  [Delete]                 │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚪ Staging Postgres                                   │  │
│  │    postgres • staging.internal:5432                   │  │
│  │    50 tables allowed, 0 excluded                      │  │
│  │                                                       │  │
│  │       [Activate]  [Edit]  [Test]  [Delete]            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ ⚪ BigQuery Analytics                                 │  │
│  │    bigquery • project-123                             │  │
│  │    120 tables allowed, 5 excluded                     │  │
│  │                                                       │  │
│  │       [Activate]  [Edit]  [Test]  [Delete]            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**States:**
- **No connections:** Show empty state with "Create your first connection" prompt
- **Connections exist:** List as cards
- **Active connection:** Green dot, "Active" badge, no "Activate" button
- **Inactive connections:** Gray dot, "Activate" button visible

**Actions:**
- `[+ New]` — Opens connection form modal (empty)
- `[Edit]` — Opens connection form modal (prefilled, read-only until edit enabled)
- `[Test]` — Tests saved connection, shows result inline
- `[Delete]` — Shows confirmation dialog
- `[Activate]` — Sets as active connection

---

### 3. Connection Form (Modal)

Opened by: `[+ New]` or `[Edit]`

```
┌─────────────────────────────────────────────────────────────┐
│  New Connection                                    [X]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Connection Name:  [Production MySQL____________]           │
│                                                             │
│  Database Type:    [MySQL ▼]                                │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Host:      [prod-db.rds.amazonaws.com___________]      │ │
│  │ Port:      [3306_______________________________]       │ │
│  │ Database:  [myapp______________________________]       │ │
│  │ Username:  [admin______________________________]       │ │
│  │ Password:  [••••••••___________________________]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  [Test Connection]                                          │
│                                                             │
│  ✅ Connection successful (230ms)                           │
│                                                             │
│─────────────────────────────────────────────────────────────│
│                                                             │
│  Debug Access:                                              │
│                                                             │
│  ⚠ Views referencing excluded tables are not auto-detected. │
│    Debugging such views is your responsibility.             │
│                                                             │
│  [Include All]  [Exclude All]    Search: [________] 🔍     │
│                                                             │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ ▼ ☑ public                                            │ │
│  │     ☑ orders                                          │ │
│  │     ☑ products                                        │ │
│  │     ☑ categories                                      │ │
│  │     ☐ internal_config          ← excluded             │ │
│  │ ▼ ☐ sensitive                  ← excluded (schema)    │ │
│  │     ☐ users                    ← inherited            │ │
│  │     ☐ payments                 ← inherited            │ │
│  │     ☐ audit_log                ← inherited            │ │
│  │ ▶ ☑ analytics                  (collapsed)            │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  Summary: 47 included, 4 excluded (1 schema, 1 table)      │
│                                                             │
│─────────────────────────────────────────────────────────────│
│                                                             │
│  Review:                                                    │
│  • Connection: Production MySQL (mysql)                     │
│  • Host: prod-db.rds.amazonaws.com:3306                     │
│  • Debug access: 47 included, 4 excluded                    │
│                                                             │
│                          [Cancel]  [Save Connection]        │
└─────────────────────────────────────────────────────────────┘
```

**Database-specific fields:**

| DB Type | Fields |
|---------|--------|
| Postgres | Host, Port, Database, Username, Password |
| MySQL | Host, Port, Database, Username, Password |
| BigQuery | Project ID, Dataset, Service Account JSON (file upload or paste) |
| Snowflake | Account, Warehouse, Database, Schema, Username, Password |

**Debug Access Tree UX:**

- ☑ Checked = included in debugging context
- ☐ Unchecked = excluded from debugging context
- Tree hierarchy matches DB structure (see Excludable Levels table)
- Parent checkbox = toggle all children
- Unchecking a parent = excludes at parent level (explicit), all children inherited
- Checking one child under excluded parent = includes that child, parent no longer explicitly excluded, remaining siblings stay individually excluded
- Collapsed nodes show aggregate status
- Grey text + "excluded" label on excluded entities
- "inherited" label on children excluded via parent
- `[Include All]` = checks all boxes, clears all exclusions
- `[Exclude All]` = unchecks all boxes, excludes at top level
- Search filters tree by name (matches at any level)
- Summary shows counts with breakdown

**Edit Mode:**
- Form fields are read-only by default when editing
- User clicks `[Edit]` to enable editing
- Once editing, `[Cancel]` reverts changes, `[Save]` saves

**States:**
- **Form empty:** Test and Save disabled
- **Form partially filled:** Test and Save disabled, indicate required fields
- **Form filled:** Test enabled
- **Testing:** Test button shows spinner, disabled
- **Test success:** Show "✅ Connection successful (Xms)", load entity tree
- **Test failed:** Show "❌ Connection failed. Verify credentials."
- **Saving:** Save button shows spinner, disabled
- **Save with untested changes:** Show confirmation dialog

---

### 4. Confirmation Dialog (Untested Save)

```
┌─────────────────────────────────────────────────────────────┐
│  Save without testing?                                      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Connection parameters have changed since last test.        │
│  Save anyway?                                               │
│                                                             │
│                          [Cancel]  [Save Anyway]            │
└─────────────────────────────────────────────────────────────┘
```

**Logic:**
- Show only if `hasChanges && !wasTested`
- If no changes made (edit mode, just viewing), no warning
- If changes made and tested, no warning

---

### 5. Delete Confirmation Dialog

```
┌─────────────────────────────────────────────────────────────┐
│  Delete connection?                                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Are you sure you want to delete "Production MySQL"?        │
│  This cannot be undone.                                     │
│                                                             │
│                             [Cancel]  [Delete]              │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. Local Backend Not Running Warning

Shown when UI cannot reach local backend:

```
┌─────────────────────────────────────────────────────────────┐
│  ⚠️ Local backend not running                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  To connect to your database, start the local backend:      │
│                                                             │
│  pip install sql-debugger                                   │
│  sql-debugger start                                         │
│                                                             │
│                                       [Retry Connection]    │
└─────────────────────────────────────────────────────────────┘
```

---

## Endpoints

All endpoints on **Local Backend** (localhost:8765).

### Endpoint Summary

| Method | Path | Function Name | Purpose |
|--------|------|---------------|---------|
| GET | `/health` | `health_check` | Check local backend is running |
| GET | `/connections` | `list_connections` | List all saved connections |
| POST | `/connections` | `create_connection` | Create new connection |
| GET | `/connections/{id}` | `get_connection` | Get single connection |
| PUT | `/connections/{id}` | `update_connection` | Update connection params |
| DELETE | `/connections/{id}` | `delete_connection` | Delete connection |
| POST | `/connections/test` | `test_connection` | Test connection params |
| POST | `/connections/{id}/activate` | `activate_connection` | Set as active |
| GET | `/connections/active` | `get_active_connection` | Get active connection |
| GET | `/connections/{id}/entities` | `list_entities` | List entity tree with exclusion status |
| POST | `/connections/{id}/entities/exclude` | `exclude_entities` | Exclude entities from debugging |
| POST | `/connections/{id}/entities/include` | `include_entities` | Include entities in debugging |
| POST | `/connections/{id}/entities/exclude-all` | `exclude_all_entities` | Exclude all entities |
| POST | `/connections/{id}/entities/include-all` | `include_all_entities` | Include all entities |

---

### Endpoint Details

#### `GET /health`

Check if local backend is running.

**Response (200):**
```json
{
  "status": "ok",
  "version": "0.1.0"
}
```

**Failure:** Connection refused → UI shows "Local backend not running"

---

#### `GET /connections`

List all saved connections.

**Response (200):**
```json
{
  "connections": [
    {
      "id": "abc123",
      "name": "Production MySQL",
      "db_type": "mysql",
      "host": "prod-db.rds.amazonaws.com",
      "port": 3306,
      "database": "myapp",
      "username": "admin",
      "is_active": true,
      "entities_included": 47,
      "entities_excluded": 4
    }
  ]
}
```

**Note:** Password never returned in any endpoint.

---

#### `POST /connections`

Create new connection.

**Request:**
```json
{
  "name": "Production MySQL",
  "db_type": "mysql",
  "host": "prod-db.rds.amazonaws.com",
  "port": 3306,
  "database": "myapp",
  "username": "admin",
  "password": "secret123"
}
```

**Response (201):**
```json
{
  "id": "abc123",
  "name": "Production MySQL",
  "db_type": "mysql"
}
```

**Error (400):**
```json
{
  "error": "Connection name already exists"
}
```

---

#### `GET /connections/{id}`

Get single connection details.

**Response (200):**
```json
{
  "id": "abc123",
  "name": "Production MySQL",
  "db_type": "mysql",
  "host": "prod-db.rds.amazonaws.com",
  "port": 3306,
  "database": "myapp",
  "username": "admin",
  "is_active": true,
  "entities_included": 47,
  "entities_excluded": 4
}
```

**Error (404):**
```json
{
  "error": "Connection not found"
}
```

---

#### `PUT /connections/{id}`

Update connection params.

**Request:**
```json
{
  "name": "Production MySQL (updated)",
  "host": "new-host.rds.amazonaws.com",
  "password": "newsecret"
}
```

**Response (200):**
```json
{
  "id": "abc123",
  "name": "Production MySQL (updated)",
  "db_type": "mysql"
}
```

**Note:** Only include fields that changed. Password optional (omit to keep existing).

---

#### `DELETE /connections/{id}`

Delete connection.

**Response (204):** No content

**Error (404):**
```json
{
  "error": "Connection not found"
}
```

**Error (400):**
```json
{
  "error": "Cannot delete active connection. Activate another connection first."
}
```

---

#### `POST /connections/test`

Test connection. Can test new params or existing saved connection.

**Request (new connection):**
```json
{
  "db_type": "mysql",
  "host": "prod-db.rds.amazonaws.com",
  "port": 3306,
  "database": "myapp",
  "username": "admin",
  "password": "secret123"
}
```

**Request (existing connection):**
```json
{
  "connection_id": "abc123"
}
```

**Request (test edits before saving):**
```json
{
  "connection_id": "abc123",
  "host": "new-host.rds.amazonaws.com",
  "password": "newsecret"
}
```

**Response (200) - Success:**
```json
{
  "success": true,
  "latency_ms": 230
}
```

**Response (200) - Failure:**
```json
{
  "success": false,
  "error": "Connection failed. Verify credentials."
}
```

**Timeout (10s):**
```json
{
  "success": false,
  "error": "Connection timed out. Check network."
}
```

---

#### `POST /connections/{id}/activate`

Set connection as active.

**Response (200):**
```json
{
  "success": true,
  "active_connection_id": "abc123"
}
```

---

#### `GET /connections/active`

Get currently active connection.

**Response (200):**
```json
{
  "id": "abc123",
  "name": "Production MySQL",
  "db_type": "mysql",
  "host": "prod-db.rds.amazonaws.com",
  "port": 3306,
  "database": "myapp",
  "username": "admin",
  "entities_included": 47,
  "entities_excluded": 4
}
```

**Response (200) - No active connection:**
```json
{
  "id": null
}
```

---

#### `GET /connections/{id}/entities`

List entity tree with exclusion status. Returns hierarchical structure matching DB type.

**Response (200) — Postgres example:**
```json
{
  "db_type": "postgres",
  "excludable_levels": ["schema", "table"],
  "tree": [
    {
      "level": "schema",
      "name": "public",
      "excluded": false,
      "children": [
        { "level": "table", "name": "orders", "excluded": false },
        { "level": "table", "name": "products", "excluded": false },
        { "level": "table", "name": "internal_config", "excluded": true, "exclusion_source": "direct" }
      ]
    },
    {
      "level": "schema",
      "name": "sensitive",
      "excluded": true,
      "exclusion_source": "direct",
      "children": [
        { "level": "table", "name": "users", "excluded": true, "exclusion_source": "inherited" },
        { "level": "table", "name": "payments", "excluded": true, "exclusion_source": "inherited" }
      ]
    }
  ],
  "summary": {
    "total_tables": 51,
    "included": 47,
    "excluded": 4
  }
}
```

**Response (200) — Snowflake example:**
```json
{
  "db_type": "snowflake",
  "excludable_levels": ["database", "schema", "table"],
  "tree": [
    {
      "level": "database",
      "name": "prod",
      "excluded": false,
      "children": [
        {
          "level": "schema",
          "name": "public",
          "excluded": false,
          "children": [
            { "level": "table", "name": "orders", "excluded": false },
            { "level": "table", "name": "api_keys", "excluded": true, "exclusion_source": "direct" }
          ]
        },
        {
          "level": "schema",
          "name": "pii_schema",
          "excluded": true,
          "exclusion_source": "direct",
          "children": [
            { "level": "table", "name": "users", "excluded": true, "exclusion_source": "inherited" }
          ]
        }
      ]
    }
  ],
  "summary": {
    "total_tables": 25,
    "included": 23,
    "excluded": 2
  }
}
```

`exclusion_source`: `"direct"` = user explicitly excluded this entity. `"inherited"` = excluded because parent is excluded.

---

#### `POST /connections/{id}/entities/exclude`

Exclude entities from debugging.

**Request:**
```json
{
  "entities": [
    { "level": "schema", "name": "sensitive" },
    { "level": "table", "path": { "schema": "public" }, "name": "internal_config" }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "total_tables": 51,
    "included": 47,
    "excluded": 4
  }
}
```

---

#### `POST /connections/{id}/entities/include`

Include entities in debugging.

**Request:**
```json
{
  "entities": [
    { "level": "table", "path": { "schema": "sensitive" }, "name": "public_metrics" }
  ]
}
```

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "total_tables": 51,
    "included": 48,
    "excluded": 3
  }
}
```

**Note:** Including a table under an excluded schema removes the schema from `blocked_schemas` and keeps remaining siblings individually excluded.

---

#### `POST /connections/{id}/entities/exclude-all`

Exclude all entities.

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "total_tables": 51,
    "included": 0,
    "excluded": 51
  }
}
```

---

#### `POST /connections/{id}/entities/include-all`

Include all entities.

**Response (200):**
```json
{
  "success": true,
  "summary": {
    "total_tables": 51,
    "included": 51,
    "excluded": 0
  }
}
```

---

## Error Handling

### Security: Generic Error Messages

| Actual Error | User Sees |
|--------------|-----------|
| Wrong password | "Connection failed. Verify credentials." |
| Host unreachable | "Connection failed. Verify host and port." |
| Database not found | "Connection failed. Verify database name." |
| Timeout | "Connection timed out. Check network." |
| Permission denied | "Connection failed. Verify permissions." |
| Connection not found | "Connection not found." |

**Rationale:** Don't reveal specific failure reasons that could aid attackers.

---

## Tests

### UI Tests

| # | Test | Type |
|---|------|------|
| 1 | Connection icon in header opens panel | Unit |
| 2 | Empty state shows when no connections | Unit |
| 3 | Connection cards display correct info | Unit |
| 4 | `[+ New]` opens form modal | Unit |
| 5 | `[Edit]` opens form modal with prefilled data (read-only) | Unit |
| 6 | Edit button enables form fields | Unit |
| 7 | DB type dropdown changes visible fields | Unit |
| 8 | Test button disabled until required fields filled | Unit |
| 9 | Test button disabled and shows spinner during request | Unit |
| 10 | Test button re-enabled after response | Unit |
| 11 | Test success shows checkmark and latency | Unit |
| 12 | Test failure shows generic error message | Unit |
| 13 | Entity tree appears after successful test | Integration |
| 14 | Entity tree shows correct hierarchy per DB type | Unit |
| 15 | Search filters entity tree | Unit |
| 16 | Include All checks all boxes at all levels | Unit |
| 17 | Exclude All unchecks all boxes at all levels | Unit |
| 18 | Excluding parent unchecks all children (inherited) | Unit |
| 19 | Including one child under excluded parent: parent unchecked, child checked, siblings remain unchecked | Unit |
| 20 | "inherited" label shown on children of excluded parent | Unit |
| 21 | "excluded" label shown on directly excluded entities | Unit |
| 22 | Summary shows correct counts with breakdown | Unit |
| 23 | Collapsed parent shows aggregate exclusion status | Unit |
| 24 | View warning notice displayed in entity access section | Unit |
| 25 | Review section shows connection summary | Unit |
| 26 | Save shows confirmation if changes untested | Unit |
| 27 | Save button disabled and shows spinner during request | Unit |
| 28 | Save button re-enabled after response | Unit |
| 29 | Save button stays disabled if no changes (edit mode) | Unit |
| 30 | Delete shows confirmation dialog | Unit |
| 31 | Delete removes connection from list | Integration |
| 32 | Activate sets connection as active | Integration |
| 33 | Active connection shows in header | Integration |
| 34 | Local backend not running shows warning | Integration |
| 35 | Health check returns 200 | Integration |
| 36 | Can see all connections | Integration |

---

## Decisions Log

Decisions made during design, for future reference.

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Multiple connections | Yes, one active at a time | Users have prod/staging/dev |
| Entity access model | Hierarchical tree with checkboxes, Include All / Exclude All | Scales to BigQuery/Snowflake with hundreds of tables |
| Terminology | "Excluded from debugging" not "blocked" | Clarifies that users can still query excluded entities |
| Denormalized storage | Store exclusions at both parent and table level | Fast reads — O(1) lookup for "is this table excluded?" |
| No auto-promotion | Individually excluding all tables ≠ excluding the schema | Avoids ambiguity when new tables appear |
| Keyring | Use OS keyring with encrypted file fallback | Secure, standard approach |
| Multi-tab | Allow (stateless design) | Simpler than blocking, no sync needed |
| Auth local↔cloud | None needed for MVP | Local backend doesn't talk to cloud |
| Error messages | Generic for security | Don't reveal specific failure reasons |
| Edit mode | Read-only by default, explicit Edit button | Prevents accidental changes |
| Test before save | Warning if changes untested | Prevents saving broken connections |
| Endpoint naming | REST convention + descriptive function names | Standard, Swagger shows operation names |
| Combined test endpoint | Single `/connections/test` with optional params | Simpler API |
| View warning | User-facing notice, not automatic detection | Scanning view definitions across 4 DB types is too complex for MVP |

---

*End of Connection Management Frontend Spec v2*
