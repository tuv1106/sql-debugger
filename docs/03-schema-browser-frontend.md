# SQL Debugger — Schema Browser Frontend Spec

**Version:** 1.0
**Date:** February 2026
**Status:** Draft
**Dependencies:** `01-connection-management-frontend.md` (v2), `02-connection-management-backend.md` (v2)

---

## Table of Contents

1. [Feature Description](#feature-description)
2. [Scope](#scope)
3. [UI Components](#ui-components)
4. [Data Flow](#data-flow)
5. [Endpoints](#endpoints)
6. [Error Handling](#error-handling)
7. [Tests](#tests)
8. [Decisions Log](#decisions-log)

---

## Feature Description

### Goal

Let users browse their database structure (schemas, tables, columns with types) while seeing which entities are excluded from AI debugging.

### What It Solves

- Users need to see what's in their database before writing or debugging queries
- Users need to know which tables are excluded from AI context
- Query Console and Lineage features will reference schema for validation and display

### User Flow

1. User has an active connection
2. User opens Schema Browser panel (toggle button in toolbar)
3. Schema loads from cache immediately (if available), refreshes in background
4. User browses: schemas/databases → tables → columns (with types)
5. Excluded entities shown in grey
6. User can search/filter by name
7. User can manually refresh

---

## Scope

### In MVP

| Feature | Included |
|---------|----------|
| Hierarchical tree (matches DB structure) | ✅ |
| Column names and types | ✅ |
| Excluded entities shown (grey, labeled) | ✅ |
| Free text search on entity names | ✅ |
| Stale-while-revalidate caching (localStorage) | ✅ |
| Manual refresh button | ✅ |
| Auto-refresh on connection select | ✅ |
| Auto-refresh on session start (page load) | ✅ |
| Auto-refresh after DDL detected | ✅ |
| Default hidden, toggle button to show | ✅ |

### Out of MVP

| Feature | Reason |
|---------|--------|
| Constraints (PK, FK, NOT NULL) | Complexity varies across DB types, reassess post-MVP |
| Column search (across tables) | Nice-to-have, table-level search sufficient |
| Schema diffing / change history | Separate feature |
| Drag-to-query (drag table into console) | Nice-to-have |
| Table row counts | Requires query per table, expensive |
| Table/column comments/descriptions | Not consistent across DB types |

### Constraints — Deferred Analysis

Column types are available from `INFORMATION_SCHEMA` or equivalent on all 4 DBs with a single query. Constraints (PK, FK, indexes, nullable) require additional queries and differ significantly:

| DB | Types Query | Constraints Query | Complexity |
|----|-------------|-------------------|------------|
| Postgres | `information_schema.columns` | `pg_constraint`, `pg_index` | Medium — joins needed |
| MySQL | `information_schema.columns` | `information_schema.key_column_usage` | Low |
| BigQuery | `INFORMATION_SCHEMA.COLUMNS` | No traditional constraints | N/A |
| Snowflake | `information_schema.columns` | `information_schema.table_constraints` | Medium |

Recommendation: revisit constraints after MVP. Types are free, constraints are not.

---

## UI Components

### 1. Schema Browser Toggle

Location: Left side of main toolbar / header area.

```
┌─────────────────────────────────────────────────────────────┐
│  [📋] SQL Debugger       🔌 Production MySQL ▼     [user]  │
└─────────────────────────────────────────────────────────────┘
  ^
  Toggle button (opens/closes Schema Browser panel)
```

**States:**
- Panel closed (default): icon only, no panel visible
- Panel open: left sidebar panel visible

---

### 2. Schema Browser Panel (Left Sidebar)

```
┌──────────────────────────┬──────────────────────────────────┐
│  Schema Browser    [↻] [X]│                                 │
│                           │                                 │
│  Search: [________] 🔍   │        (Main content area:      │
│                           │         Query Console,          │
│  ▼ public                 │         Lineage, Results)       │
│    ▼ orders               │                                 │
│      id         INTEGER   │                                 │
│      user_id    INTEGER   │                                 │
│      status     VARCHAR   │                                 │
│      created_at TIMESTAMP │                                 │
│    ▶ products             │                                 │
│    ▶ categories           │                                 │
│    ▼ internal_config  ⊘   │                                 │
│      key        VARCHAR   │                                 │
│      value      TEXT      │                                 │
│                           │                                 │
│  ▼ sensitive          ⊘   │                                 │
│    ▶ users            ⊘   │                                 │
│    ▶ payments         ⊘   │                                 │
│    ▶ audit_log        ⊘   │                                 │
│                           │                                 │
│  ▶ analytics              │                                 │
│                           │                                 │
│  51 tables (4 excluded)   │                                 │
│                           │                                 │
└──────────────────────────┴──────────────────────────────────┘
```

**Tree hierarchy per DB type:**

| DB | Level 1 | Level 2 | Level 3 | Level 4 |
|----|---------|---------|---------|---------|
| Postgres | schema | table | column | — |
| MySQL | database | table | column | — |
| BigQuery | dataset | table | column | — |
| Snowflake | database | schema | table | column |

**Visual indicators:**
- `▶` collapsed node (has children)
- `▼` expanded node
- `⊘` excluded from debugging (grey text + icon)
- Excluded entities: grey text, `⊘` icon, tooltip "Excluded from AI debugging"
- Inherited exclusion (parent excluded): same grey style, tooltip "Excluded — inherited from [parent name]"
- Column type shown right-aligned in monospace, muted color

**Interactions:**
- Click `▶`/`▼` to expand/collapse
- Click table name → no action in MVP (future: select for query console)
- `[↻]` refresh button — fetches fresh schema
- `[X]` close button — hides panel
- Search filters at all levels (schema names, table names)

---

### 3. Schema Browser States

**No active connection:**
```
┌──────────────────────────┐
│  Schema Browser    [X]   │
│                          │
│                          │
│  No active connection.   │
│                          │
│  [Open Connections]      │
│                          │
└──────────────────────────┘
```

**Loading (first time, no cache):**
```
┌──────────────────────────┐
│  Schema Browser  [↻] [X] │
│                          │
│  ┌────────────────────┐  │
│  │ ▓▓▓▓▓▓░░░░░░░░░░  │  │
│  │ Loading schema...  │  │
│  └────────────────────┘  │
│                          │
└──────────────────────────┘
```

**Loading (cached, refreshing in background):**
```
┌──────────────────────────┐
│  Schema Browser  [↻] [X] │
│  Refreshing...           │
│                          │
│  (cached tree shown      │
│   normally)              │
│                          │
└──────────────────────────┘
```

Small "Refreshing..." indicator at top. Tree is fully interactive.

**Error (fetch failed):**
```
┌──────────────────────────┐
│  Schema Browser  [↻] [X] │
│                          │
│  Failed to load schema.  │
│  [Retry]                 │
│                          │
│  (cached tree shown if   │
│   available, with stale  │
│   warning)               │
│                          │
└──────────────────────────┘
```

**Empty schema (connection works but 0 tables):**
```
┌──────────────────────────┐
│  Schema Browser  [↻] [X] │
│                          │
│  No tables found.        │
│  Check database          │
│  permissions.            │
│                          │
└──────────────────────────┘
```

**Search with no results:**
```
┌──────────────────────────┐
│  Schema Browser  [↻] [X] │
│                          │
│  Search: [orders___] 🔍  │
│                          │
│  No matching entities.   │
│                          │
└──────────────────────────┘
```

---

## Data Flow

### Schema Fetch + Cache Strategy

```
Page Load / Connection Select
         │
         ▼
   Cache exists for this connection_id?
    ├── YES → Show cached tree immediately
    │         Fetch fresh schema in background
    │         On response: diff + merge (no flash)
    │
    └── NO → Show loading skeleton
             Fetch schema
             On response: render tree, save to cache
```

### Cache Details

| Property | Value |
|----------|-------|
| Storage | localStorage |
| Key | `schema_cache_{connection_id}` |
| Contents | Full schema tree JSON + timestamp |
| Invalidation | On connection delete, on manual refresh, on DDL detected |
| Stale tolerance | No expiry — always show stale, always refresh in background |

### DDL Detection

When user executes a query (via Query Console), before execution:
1. sqlglot parses the query
2. If statement type is DDL (CREATE, ALTER, DROP, RENAME, TRUNCATE) → flag
3. After execution completes: trigger schema refresh
4. Non-DDL queries (SELECT, INSERT, UPDATE, DELETE) → no refresh

This is free because sqlglot already parses the query for lineage visualization.

### Refresh Triggers Summary

| Trigger | Behavior |
|---------|----------|
| Connection select (activate) | Background refresh, show cache if available |
| Session start (page load with active connection) | Background refresh, show cache if available |
| DDL detected after query execution | Background refresh |
| Manual refresh button [↻] | Foreground refresh with "Refreshing..." indicator |

---

## Endpoints

### New Endpoint (Local Backend)

#### `GET /connections/{id}/schema`

Returns full schema tree with column info and exclusion status.

**Response (200) — Postgres example:**
```json
{
  "db_type": "postgres",
  "tree": [
    {
      "name": "public",
      "level": "schema",
      "excluded": false,
      "children": [
        {
          "name": "orders",
          "level": "table",
          "excluded": false,
          "columns": [
            { "name": "id", "type": "integer" },
            { "name": "user_id", "type": "integer" },
            { "name": "status", "type": "character varying(50)" },
            { "name": "created_at", "type": "timestamp with time zone" }
          ]
        },
        {
          "name": "internal_config",
          "level": "table",
          "excluded": true,
          "exclusion_source": "direct",
          "columns": [
            { "name": "key", "type": "character varying(255)" },
            { "name": "value", "type": "text" }
          ]
        }
      ]
    },
    {
      "name": "sensitive",
      "level": "schema",
      "excluded": true,
      "exclusion_source": "direct",
      "children": [
        {
          "name": "users",
          "level": "table",
          "excluded": true,
          "exclusion_source": "inherited",
          "columns": [
            { "name": "id", "type": "integer" },
            { "name": "email", "type": "character varying(255)" }
          ]
        }
      ]
    }
  ],
  "summary": {
    "total_schemas": 3,
    "total_tables": 51,
    "excluded_schemas": 1,
    "excluded_tables": 4
  },
  "fetched_at": "2026-02-22T14:30:00Z"
}
```

**Response (200) — Snowflake example:**
```json
{
  "db_type": "snowflake",
  "tree": [
    {
      "name": "PROD",
      "level": "database",
      "excluded": false,
      "children": [
        {
          "name": "PUBLIC",
          "level": "schema",
          "excluded": false,
          "children": [
            {
              "name": "ORDERS",
              "level": "table",
              "excluded": false,
              "columns": [
                { "name": "ID", "type": "NUMBER(38,0)" },
                { "name": "STATUS", "type": "VARCHAR(50)" }
              ]
            }
          ]
        }
      ]
    }
  ],
  "summary": {
    "total_databases": 2,
    "total_schemas": 5,
    "total_tables": 120,
    "excluded_databases": 1,
    "excluded_schemas": 1,
    "excluded_tables": 15
  },
  "fetched_at": "2026-02-22T14:30:00Z"
}
```

**Response (404):** Connection not found.

**Response (503):** Database unreachable (connection failed during schema fetch).

---

### Existing Endpoint Changes

The `GET /connections/{id}/entities` endpoint from the Connection Management spec returns the entity tree **without columns** (for the exclusion config UI). The new `GET /connections/{id}/schema` endpoint returns the full tree **with columns** (for the Schema Browser).

| Endpoint | Columns? | Purpose |
|----------|----------|---------|
| `GET /connections/{id}/entities` | No | Connection form — entity exclusion config |
| `GET /connections/{id}/schema` | Yes | Schema Browser — full browsing |

Both endpoints include `excluded` and `exclusion_source` fields.

---

## Backend Implementation Notes

### Schema Query Per DB Type

| DB | Query Source | Notes |
|----|-------------|-------|
| Postgres | `information_schema.columns` | Filter by schema, exclude `pg_catalog`, `information_schema` |
| MySQL | `information_schema.columns` | Filter by database |
| BigQuery | `INFORMATION_SCHEMA.COLUMNS` per dataset | May need one query per dataset |
| Snowflake | `information_schema.columns` | Filter by database, schema |

### Column Type Representation

Types are returned as-is from the database. No normalization.

| DB | Example types |
|----|---------------|
| Postgres | `integer`, `character varying(255)`, `timestamp with time zone`, `boolean` |
| MySQL | `int`, `varchar(255)`, `datetime`, `tinyint(1)` |
| BigQuery | `STRING`, `INT64`, `TIMESTAMP`, `FLOAT64`, `BOOL` |
| Snowflake | `NUMBER(38,0)`, `VARCHAR(16777216)`, `TIMESTAMP_NTZ(9)` |

### Performance

Schema fetch involves 1 query per DB type (BigQuery may need 1 per dataset). Expected latency:

| Scenario | Expected Latency |
|----------|-----------------|
| Small DB (< 50 tables) | < 1s |
| Medium DB (50-500 tables) | 1-3s |
| Large DB (500+ tables) | 3-10s |

This is why the stale-while-revalidate cache matters — users see cached data instantly while fresh data loads.

---

## Error Handling

| Error Condition | User Sees | Behavior |
|-----------------|-----------|----------|
| No active connection | "No active connection" + link to connections | Empty state |
| Connection failed during fetch | "Failed to load schema" + Retry button | Show cached if available |
| Timeout (> 30s) | "Schema fetch timed out" + Retry button | Show cached if available |
| 0 tables returned | "No tables found. Check database permissions." | Empty state |
| Connection deleted while panel open | Panel resets to "No active connection" state | Clears cache for that connection |

---

## Tests

### UI Tests

| # | Test | Type |
|---|------|------|
| 1 | Toggle button opens/closes Schema Browser panel | Unit |
| 2 | Panel closed by default on first visit | Unit |
| 3 | Panel state persists in session (open stays open) | Unit |
| 4 | No active connection shows empty state with link | Unit |
| 5 | Loading state shows skeleton (no cache) | Unit |
| 6 | Loading state shows cached tree + "Refreshing..." (with cache) | Unit |
| 7 | Tree renders correct hierarchy for Postgres (schema → table → column) | Unit |
| 8 | Tree renders correct hierarchy for MySQL (database → table → column) | Unit |
| 9 | Tree renders correct hierarchy for BigQuery (dataset → table → column) | Unit |
| 10 | Tree renders correct hierarchy for Snowflake (database → schema → table → column) | Unit |
| 11 | Column types displayed right-aligned in muted monospace | Unit |
| 12 | Expand/collapse nodes works | Unit |
| 13 | Excluded entity shows grey text + ⊘ icon | Unit |
| 14 | Directly excluded entity tooltip shows "Excluded from AI debugging" | Unit |
| 15 | Inherited excluded entity tooltip shows "Excluded — inherited from [parent]" | Unit |
| 16 | Search filters tree by name at all levels | Unit |
| 17 | Search with no results shows "No matching entities" | Unit |
| 18 | Search is case-insensitive | Unit |
| 19 | Clear search restores full tree | Unit |
| 20 | Refresh button triggers schema fetch | Unit |
| 21 | "Refreshing..." indicator shown during background refresh | Unit |
| 22 | Summary footer shows correct counts | Unit |
| 23 | Error state shows retry button | Unit |
| 24 | Error state shows cached tree if available + stale warning | Unit |
| 25 | Empty schema shows "No tables found" message | Unit |

### Integration Tests

| # | Test | Type |
|---|------|------|
| 26 | Connection select triggers schema fetch | Integration |
| 27 | Page load with active connection triggers schema fetch | Integration |
| 28 | Schema cached in localStorage after fetch | Integration |
| 29 | Cached schema shown immediately, fresh fetch in background | Integration |
| 30 | Background refresh updates tree without flash | Integration |
| 31 | DDL execution triggers schema refresh | Integration |
| 32 | Manual refresh fetches fresh schema | Integration |
| 33 | Connection delete clears schema cache | Integration |
| 34 | Schema endpoint returns correct structure per DB type | Integration |
| 35 | Excluded entities from connection config reflected in schema tree | Integration |

### Summary: 35 tests

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Schema depth | Tables + columns with types. No constraints. | Types are one query. Constraints vary across DBs, deferred to post-MVP |
| Column types | DB-native strings, no normalization | Show what DB reports. Users know their DB's types |
| Tree hierarchy | Matches DB structure (not flattened) | Users expect it. sqlglot needs qualified names. Consistent with entity exclusion UI |
| Cache strategy | Stale-while-revalidate in localStorage | Sub-second UI for returning users. Background refresh keeps data fresh |
| Refresh triggers | Connection select, session start, DDL detected, manual | Covers all cases without wasteful refreshes |
| DDL detection | sqlglot classifies statement type | Free — sqlglot already parses for lineage |
| Default visibility | Hidden, toggle button to show | Screen real estate. Not all users need it visible |
| Excluded entity display | Grey text + ⊘ icon, still browsable | "Excluded from debugging" not "hidden". Users can still see and query |
| Separate schema endpoint | `/schema` (with columns) vs `/entities` (without) | Different consumers need different detail levels |
| System schemas | Exclude pg_catalog, information_schema, etc. from tree | Noise for users. Can revisit if requested |
| No click-to-query | Click on table does nothing in MVP | Future feature — select for Query Console |

---

## Future Considerations (Post-MVP)

| Feature | Notes |
|---------|-------|
| Constraints (PK, FK, nullable, unique) | Add to column display. Requires per-DB queries |
| Column search | Search across all tables for a column name |
| Click table → insert into Query Console | Select table name, paste into editor |
| Table row count | Show approximate counts (pg_stat, etc.) |
| Schema comparison | Diff between connections |
| Drag-and-drop into query | Drag table/column name into editor |

---

## Related Documents

- `01-connection-management-frontend.md` (v2) — Entity exclusion model
- `02-connection-management-backend.md` (v2) — Storage format, exclusion logic
- `00-project-overview.md` — MVP scope

---

*End of Schema Browser Frontend Spec*
