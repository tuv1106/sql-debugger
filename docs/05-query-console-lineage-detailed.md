# Query Console, Lineage & Results — Detailed Spec

**Version:** 1.0
**Date:** March 2026
**Status:** Approved
**Dependencies:** `01-connection-management-frontend-v2.md`, `02-connection-management-backend-v2.md`, `03-schema-browser-frontend.md`, `04-query-console-design.md` (high-level)

---

## Table of Contents

1. [Overview](#1-overview)
2. [Backend Endpoints](#2-backend-endpoints)
3. [Query Console](#3-query-console)
4. [Lineage Tab](#4-lineage-tab)
5. [Node Visual Design & Interactions](#5-node-visual-design--interactions)
6. [Breakpoints & Subtree Selection](#6-breakpoints--subtree-selection)
7. [Editor Inline Execution](#7-editor-inline-execution)
8. [Bidirectional Sync](#8-bidirectional-sync)
9. [Filter & Order Injection](#9-filter--order-injection)
10. [Graph Collapse & Focus](#10-graph-collapse--focus)
11. [Results Viewer](#11-results-viewer)
12. [Tests](#12-tests)
13. [Decisions Log](#13-decisions-log)

---

## 1. Overview

This spec details the Query Console, Lineage Visualization, and Results Viewer — the core debugging interface. It expands the high-level design in `04-query-console-design.md` with full endpoint contracts, component structure, interaction model, and test plan.

### Application Layout

```
┌─────────────┬──────────────────────────────────┬───────────┐
│   Schema    │         Query Console            │  AI Chat  │
│   Browser   │  ┌─────────────────────────────┐ │  (toggle) │
│  (toggle)   │  │ SQL editor                  │ │           │
│             │  │ SELECT * FROM orders o      │ │           │
│  tables     │  │ LEFT JOIN products p        │ │           │
│  └ columns  │  │   ON o.product_id = ...     │ │           │
│             │  └─────────────────────────────┘ │           │
│             │  [Visualize]        [Run ▶]       │           │
│             │  [Upload .sql]                    │           │
│             │  ⚡ 2 filters active              │           │
│             ├──────────────────────────────────┤           │
│             │ [Lineage]  [Results]              │           │
│             │  (bottom drawer — collapsible)    │           │
└─────────────┴──────────────────────────────────┴───────────┘
```

All panel splits are draggable and resizable.

---

## 2. Backend Endpoints

Five endpoints on the **Local Backend** (localhost:8765).

### Endpoint Summary

| Method | Path | Purpose | DB call? |
|--------|------|---------|----------|
| POST | `/query/parse` | Parse SQL → lineage graph | No |
| POST | `/connections/{id}/execute` | Execute full query with injections | Yes |
| POST | `/connections/{id}/execute-node` | Execute a node's subtree with injections | Yes |
| POST | `/query/effective-sql` | Return modified SQL string (no execution) | No |
| POST | `/connections/{id}/cancel` | Cancel a running query | Yes |

### Backend State

The backend caches the latest parse result in memory (keyed by the parsed SQL). Execute-node references this cached parse to resolve the dependency graph.

- Single-user local tool — one active query at a time
- If no cached parse exists (server restart), execute-node returns 400 "Parse query first"
- Parse cache is updated on every `/query/parse` call

---

### `POST /query/parse`

Parse SQL into a lineage graph. No DB connection needed.

**Request:**
```json
{
  "sql": "WITH orders AS (\n  SELECT * FROM raw_orders WHERE status = 'complete'\n),\nenriched AS (\n  SELECT o.*, p.price\n  FROM orders o\n  LEFT JOIN products p ON o.product_id = p.product_id\n)\nSELECT * FROM enriched",
  "dialect": "postgres"
}
```

**Response (200):**
```json
{
  "nodes": [
    {
      "id": "orders",
      "type": "cte",
      "name": "orders",
      "sql": "SELECT * FROM raw_orders WHERE status = 'complete'",
      "source_position": {
        "start_line": 2,
        "start_col": 2,
        "end_line": 2,
        "end_col": 52
      },
      "depends_on": ["public.raw_orders"]
    },
    {
      "id": "public.raw_orders",
      "type": "table_source",
      "name": "public.raw_orders",
      "source_position": {
        "start_line": 2,
        "start_col": 16,
        "end_line": 2,
        "end_col": 26
      },
      "depends_on": []
    },
    {
      "id": "enriched",
      "type": "cte",
      "name": "enriched",
      "sql": "SELECT o.*, p.price\n  FROM orders o\n  LEFT JOIN products p ON o.product_id = p.product_id",
      "source_position": {
        "start_line": 4,
        "start_col": 2,
        "end_line": 7,
        "end_col": 50
      },
      "depends_on": ["orders", "public.products"]
    },
    {
      "id": "public.products",
      "type": "table_source",
      "name": "public.products",
      "source_position": {
        "start_line": 6,
        "start_col": 12,
        "end_line": 6,
        "end_col": 20
      },
      "depends_on": []
    }
  ],
  "edges": [
    { "from": "public.raw_orders", "to": "orders" },
    { "from": "orders", "to": "enriched" },
    { "from": "public.products", "to": "enriched" }
  ],
  "root_node_id": "enriched",
  "precedence_order": ["orders", "enriched"]
}
```

**Node types:** `cte`, `subquery`, `table_source`

**Node ID format (no type prefixes — SQL prevents collisions):**

| Node type | ID | Example |
|-----------|-----|---------|
| CTE | `{name}` | `orders` (unique by SQL syntax) |
| Table source | `{qualified_name}` | `public.orders` |
| Subquery | `{parent}_{alias_or_index}` | `enriched_t1`, `enriched_0` (if no alias) |

**Same table referenced multiple times** (self-join, used in multiple CTEs): one node with multiple outgoing edges.

**Table name resolution:** Table sources always display the **table name**, not any alias. `FROM products p` → node name is `products` (or `public.products`), not `p`. The parser resolves multi-part names per dialect:

| DB | Possible formats | Resolved to |
|----|-------------------|-------------|
| Postgres | `orders`, `public.orders`, `"public"."orders"` | `schema.table` |
| MySQL | `orders`, `mydb.orders`, `` `mydb`.`orders` `` | `database.table` |
| BigQuery | `orders`, `dataset.orders`, `project.dataset.orders`, backtick-quoted | `project.dataset.table` |
| Snowflake | `ORDERS`, `PUBLIC.ORDERS`, `PROD.PUBLIC.ORDERS` | `database.schema.table` |

**UNION/INTERSECT/EXCEPT branches** within a CTE: each branch is a separate `subquery` node that feeds into the CTE node.

**Recursive CTEs** (`WITH RECURSIVE`): treated as a regular CTE node. No special cycle handling.

**Subqueries in WHERE/HAVING** (`WHERE id IN (SELECT ...)`): treated as `subquery` nodes with their own dependencies.

`precedence_order` gives the narrative SQL order (top-to-bottom as written) for the precedence graph mode.

**Error (400):**
```json
{
  "error": "Parse error",
  "message": "Unexpected token at line 3, col 15",
  "position": { "line": 3, "col": 15 }
}
```

---

### `POST /connections/{id}/execute`

Execute the full query with all active injections.

**Request:**
```json
{
  "sql": "WITH orders AS (...) SELECT * FROM enriched",
  "request_id": "req_abc123",
  "injections": {
    "orders": {
      "where": "order_id = 123",
      "order_by": "created_at DESC"
    }
  },
  "limit": 1000,
  "timeout_seconds": 60
}
```

`request_id` is generated by the frontend and used for cancellation.

**Response (200):**
```json
{
  "columns": [
    { "name": "order_id", "type": "integer" },
    { "name": "price", "type": "numeric" }
  ],
  "rows": [
    [123, 45.99],
    [456, null]
  ],
  "total_rows": 2,
  "truncated": false,
  "execution_time_ms": 340
}
```

`truncated: true` when the query returned more than `limit` rows.

**Error (200 with error):**
```json
{
  "error": "Query failed",
  "message": "Column \"order_idd\" does not exist. Hint: Perhaps you meant \"order_id\".",
  "execution_time_ms": 12
}
```

Database error messages are passed through as-is (user's own DB, no security concern).

**Cancelled:**
```json
{
  "error": "cancelled"
}
```

---

### `POST /connections/{id}/execute-node`

Execute a single node's subtree with dependency resolution and injections.

**Request:**
```json
{
  "request_id": "req_def456",
  "node_id": "orders",
  "injections": {
    "orders": {
      "where": "order_id = 123"
    }
  },
  "limit": 1000,
  "timeout_seconds": 60
}
```

No `sql` field — backend uses the cached parse result from the last `/query/parse` call.

**Response:** Same structure as `/execute`.

**Backend logic:**

1. Look up cached parse result
2. Find target node by `node_id`
3. Walk dependency graph upward to collect all ancestor nodes
4. For each node bottom-up (roots/sources first): if it has injections, modify the node's SQL via sqlglot AST manipulation:
   - **WHERE injection:** Find existing WHERE clause → append with AND. No existing WHERE → add WHERE clause.
   - **ORDER BY injection:** Append ORDER BY clause.
5. Build reconstructed query (only the subtree needed for the target node)
6. Append `LIMIT` to outermost query
7. Execute against DB

**Injection composition example** — `enriched` depends on `orders`, both have injections:

```sql
-- orders has injection: WHERE order_id = 123
-- enriched has injection: WHERE price > 10

WITH orders AS (
  SELECT * FROM raw_orders
  WHERE status = 'complete' AND order_id = 123
),
enriched AS (
  SELECT o.*, p.price
  FROM orders o
  LEFT JOIN products p ON o.product_id = p.product_id
  WHERE price > 10
)
SELECT * FROM enriched
LIMIT 1000
```

Each injection modifies only its own node's SQL. Dependencies are resolved by including the full CTE chain.

**For table source nodes:** Execution generates `SELECT * FROM schema.table LIMIT {limit}` (preview).

**Error (400) — no cached parse:**
```json
{
  "error": "No parse result cached. Call /query/parse first."
}
```

**Error (400) — node not found:**
```json
{
  "error": "Node \"cte_unknown\" not found in parse result."
}
```

---

### `POST /query/effective-sql`

Return the full query with all injections applied, without executing. Used by the "View effective SQL" button.

**Request:**
```json
{
  "sql": "WITH orders AS (...) SELECT * FROM enriched",
  "injections": {
    "orders": {
      "where": "order_id = 123"
    }
  }
}
```

**Response (200):**
```json
{
  "effective_sql": "WITH orders AS (\n  SELECT * FROM raw_orders\n  WHERE status = 'complete' AND order_id = 123\n)\nSELECT * FROM enriched"
}
```

---

### `POST /connections/{id}/cancel`

Cancel a running query.

**Request:**
```json
{
  "request_id": "req_abc123"
}
```

**Response (200):**
```json
{
  "success": true
}
```

Backend maintains a map of `request_id → active DB cursor`. On cancel, kills the cursor. The pending execute request returns with `"error": "cancelled"`.

**Error (404):**
```json
{
  "error": "No active execution found for request_id."
}
```

---

### Execution Configuration

| Setting | Default | Configurable? |
|---------|---------|---------------|
| Result row limit | 1,000 | Yes (per request) |
| Query timeout | 60 seconds | Yes (per request) |

---

## 3. Query Console

### SQL Editor

- Monaco or CodeMirror with syntax highlighting
- Accepts paste or file upload via [Upload .sql]
- Always shows the **original SQL as the user wrote it** — injections are never shown in the editor
- Supports right-click context menu (see Section 7)

### Action Bar

| Button | Behavior |
|--------|----------|
| [Visualize] | Calls `/query/parse`. Opens bottom drawer to Lineage tab. Works without a DB connection. |
| [Run ▶] | Calls `/execute` with current SQL + all active injections. Opens bottom drawer to Results tab. Disabled when no active connection. |
| [Upload .sql] | File picker, replaces current editor content. |
| [Cancel] | Visible only during execution. Sends cancel for all active `request_id`s. |

All buttons disabled and show spinner during their respective operations.

### Injection Status Bar

Shown below the action bar when any injections are active:

```
⚡ 2 filters active                               [View effective SQL]
```

- Clicking "⚡ 2 filters active" toggles the Filter & Order Panel (Section 9)
- [View effective SQL] opens a read-only modal with the result of `POST /query/effective-sql`

---

## 4. Lineage Tab

Lives in the bottom drawer, alongside the Results tab.

### Two Graph Modes

Toggle in the lineage toolbar:

| Mode | Description | Default |
|------|-------------|---------|
| **Dependency graph** | DAG showing data flow — what each node depends on. Table sources are root nodes (data origins). | ✅ Yes |
| **Precedence graph** | Nodes ordered by position in the SQL as written. Shows narrative structure. | No |

### Node Types

| Type | Color | Name shown | Example |
|------|-------|-----------|---------|
| CTE | Blue | Declared name | `orders`, `enriched` |
| Subquery (with alias) | Purple | The alias | `t1`, `filtered_base` |
| Subquery (without alias) | Purple | Truncated SQL snippet | `SELECT id, price FR…` |
| Table source (root) | Green | Qualified table name | `public.raw_orders` |

Node type label (CTE / Subquery / Table) shown on hover to avoid crowding the node.

### Lineage Toolbar

```
[Dependency ✓] [Precedence]  │  [CTEs ✓] [Tables ✗] [Subqueries ✗]  │  [Run Breakpoints]  [Clear Breakpoints]  │  [Expand All] [Collapse All]
```

- Graph mode toggle (left)
- Breakpoint type filter (center) — only visible when breakpoints are set
- Breakpoint actions (center-right) — only visible when breakpoints are set
- Collapse controls (right)

### Staleness Banner

When the SQL in the editor has been edited since the last [Visualize] click:

```
⚠ Graph outdated — click Visualize to refresh
```

Visual warning only. The underlying parse data (positions, node SQL, dependencies) is kept fresh by the background re-parse (Section 8).

---

## 5. Node Visual Design & Interactions

### Node Appearance

Nodes are **color-coded by type** (Blue = CTE, Purple = Subquery, Green = Table). Type label shown on hover tooltip.

```
┌──────────────────────────┐  ← border color matches node type
│ ● orders           [▶] ⊘ │
└──────────────────────────┘
  ↑  ↑                 ↑  ↑
  │  │                 │  └─ filter indicator (when injection active)
  │  │                 └─ quick execute button
  │  └─ node name
  └─ breakpoint/status indicator

Hover tooltip: "CTE: orders" / "Table: public.orders" / "Subquery: t1"
```

### Status Indicators

| Icon | Meaning |
|------|---------|
| ○ | No breakpoint |
| ● | Breakpointed (red) |
| ✓ | Executed successfully (green) |
| ✗ | Execution failed (red) |
| ⟳ | Executing (spinner) |

### Collapsed Subtree

```
┌──────────────────────────┐
│ ○ CTE  enriched    [+5]  │
└──────────────────────────┘
```

`[+5]` badge shows the number of hidden nodes in the collapsed subtree.

### Interaction Model

| Action | Behavior |
|--------|----------|
| **Click** | Select node. Highlights corresponding SQL span in editor. |
| **Double-click** | Execute node immediately (with active injections). Result in Results tab. |
| **Right-click** | Context menu (see below) |
| **Hover** | Subtle highlight on node + its direct edges |

### Right-Click Context Menu

```
┌──────────────────────────────┐
│  Execute node                │
│  ─────────────────────────── │
│  Toggle breakpoint           │
│  Breakpoint upstream         │
│  Breakpoint downstream       │
│  ─────────────────────────── │
│  Add filter / Edit filter    │
│  ─────────────────────────── │
│  Collapse subtree            │
│  Expand subtree              │
│  ─────────────────────────── │
│  Show in editor              │
└──────────────────────────────┘
```

"Add filter" opens the Filter & Order Panel (Section 9) with a new row for that node.
"Edit filter" shown instead when the node already has an injection.

---

## 6. Breakpoints & Subtree Selection

### Setting Breakpoints

| Action | How |
|--------|-----|
| Single node | Right-click → "Toggle breakpoint", or click the breakpoint indicator on the node |
| Upstream subtree | Right-click → "Breakpoint upstream" — selects all ancestor nodes |
| Downstream subtree | Right-click → "Breakpoint downstream" — selects all dependent nodes |
| Clear all | "Clear Breakpoints" in lineage toolbar |

### Breakpoint Type Filter

After setting breakpoints, the type filter in the lineage toolbar lets users quickly include/exclude node types:

```
[CTEs ✓] [Tables ✗] [Subqueries ✗]
```

- Toggling a type off removes breakpoints from nodes of that type
- Toggling back on re-adds them
- User can then manually select/deselect individual nodes on top of the type filter

**Use case:** User selects upstream subtree (20 nodes, 12 are raw tables). Toggles off "Tables" to keep only CTEs. Then manually re-adds the one table they care about.

### Breakpoint Execution

| Aspect | Behavior |
|--------|----------|
| Trigger | Click "Run Breakpoints" in lineage toolbar |
| Parallelism | All breakpointed nodes execute in parallel (separate `/execute-node` calls) |
| Wait | Results shown only after **all** breakpointed nodes complete |
| Display | First result tab shown. **[Next]** advances to next tab in order. **[Show All]** reveals all tabs at once. |
| Tab order | Dependency order (dependency graph mode) or narrative order (precedence graph mode) |
| Cancel | Single [Cancel] button cancels all running breakpoint executions |

### Breakpoint Results Navigation

```
┌─────────────────────────────────────────────────────────────────┐
│ [orders ✓]                              [Next ▶] [Show All]     │
├─────────────────────────────────────────────────────────────────┤
│ (result table for "orders")                                     │
└─────────────────────────────────────────────────────────────────┘
```

- After all breakpoint queries complete, the first result (in order) is shown
- **[Next]** advances to the next result tab, revealing it
- **[Show All]** reveals all tabs at once (user can click any tab freely)
- Once all tabs are revealed (via Next or Show All), navigation becomes standard tab clicking

---

## 7. Editor Inline Execution

The SQL editor provides inline run affordances for all recognized SQL parts, powered by the background re-parse.

### Behavior

1. **Hover** over any recognized SQL span → subtle background highlight on the full node extent
2. **▶ appears in the gutter** at the node's start line
3. **Click ▶** → execute that node (with active injections), result in Results tab
4. **Right-click ▶** → same context menu as lineage nodes (execute, add filter, breakpoint, show in lineage)

### Node Types in Editor

| Node type | Highlight span | Execute behavior |
|-----------|---------------|-----------------|
| CTE | Full CTE definition | Reconstructs subtree + injections, executes |
| Subquery | Full subquery block | Same as CTE |
| Table source | Table name reference | `SELECT * FROM schema.table LIMIT 1000` (preview) |

### Example

Hovering over the `products` table reference:

```
     ┌─────────────────────────────────────────┐
     │ WITH orders AS (                        │
     │   SELECT * FROM raw_orders              │
     │   WHERE status = 'complete'             │
     │ ),                                      │
     │ enriched AS (                           │
     │   SELECT o.*, p.price                   │
  ▶  │   FROM orders o LEFT JOIN [products] p  │  ← highlighted
     │     ON o.product_id = p.product_id      │
     │ )                                       │
     │ SELECT * FROM enriched                  │
     └─────────────────────────────────────────┘
```

Clicking ▶ runs `SELECT * FROM products LIMIT 1000`.

### Overlapping Spans

When spans overlap (e.g., table reference inside a CTE), the **innermost node** takes priority. Right-click shows options for all enclosing nodes:

```
┌─────────────────────────────────┐
│  Execute "products" (preview)   │
│  Execute "enriched" (subtree)   │
│  ─────────────────────────────  │
│  Add filter to "enriched"       │
│  Show "enriched" in lineage     │
└─────────────────────────────────┘
```

### Prerequisites

- Gutter buttons only appear after the first successful parse (background re-parse or explicit [Visualize])
- If SQL is mid-edit and unparseable, gutter buttons use last known good parse positions

---

## 8. Bidirectional Sync

### Two Directions

| Direction | Trigger | Effect |
|-----------|---------|--------|
| Lineage → Console | Click a lineage node | Scrolls to and highlights the corresponding SQL span in the editor |
| Console → Lineage | Click or select a SQL span in the editor | Highlights the matching lineage node |

### Background Re-parse

Keeps sync accurate as the user edits:

- **Visual graph** (rendered nodes/edges in Lineage tab): only updates when user explicitly clicks [Visualize]. Stable, user-controlled.
- **Parse data** (source positions, node SQL, dependency graph): re-parsed silently in the background, 300ms after the user stops typing. No visual change to the lineage graph.

This means:
- Source positions stay accurate as the user edits → highlight sync remains correct
- Node SQL stays current → executing a node always uses the current editor content
- Dependency graph stays current → correct upstream CTEs included in node execution
- Gutter run buttons update to correct positions

**The visual graph can be stale. The data underneath never is.**

### Failure Handling

If the background re-parse fails (SQL is mid-edit and syntactically invalid):
- Use last known good positions for highlight sync
- Use last known good positions for gutter buttons
- Disable node execution with message: "Query has syntax errors — fix or click Visualize to refresh"

### Edge Case

If the user edits and clicks a node within the 300ms debounce window (before re-parse fires), the last known positions are used. The highlight may be slightly off. Acceptable for MVP.

---

## 9. Filter & Order Injection

### Model

- Injections stored **client-side** in **sessionStorage** (keyed by connection ID)
- Persist across page refresh, cleared when tab closes
- Each injection is per-node: optional WHERE clause and/or ORDER BY clause
- Passed with every execute call (node execution or full query run)

### Injection Method

Injections modify the node's SQL via **sqlglot AST manipulation** (not subquery wrapping):

| Injection type | How it's applied |
|----------------|-----------------|
| WHERE (node has existing WHERE) | Appended with AND |
| WHERE (node has no WHERE) | New WHERE clause added |
| ORDER BY | Appended to node |

**Example — node with existing WHERE:**
```sql
-- Original:
SELECT * FROM raw_orders WHERE status = 'complete'

-- After injecting WHERE order_id = 123:
SELECT * FROM raw_orders WHERE status = 'complete' AND order_id = 123
```

**Example — node with no WHERE:**
```sql
-- Original:
SELECT o.*, p.price FROM orders o LEFT JOIN products p ON ...

-- After injecting WHERE price > 10:
SELECT o.*, p.price FROM orders o LEFT JOIN products p ON ... WHERE price > 10
```

### Injection Composition Across Dependencies

When executing a node with upstream dependencies that also have injections, each node's injection is applied independently to its own SQL. The reconstructed query contains all modified CTEs in the chain.

### Filter & Order Panel

Toggled by clicking the injection status bar ("⚡ 2 filters active"). Sits between the editor and the bottom drawer.

```
┌──────────────────────────────────────────────────────────────────┐
│ Active Filters & Ordering                            [Clear All] │
├──────────────┬───────────────────────┬──────────────────┬────────┤
│ Node         │ WHERE                 │ ORDER BY         │        │
├──────────────┼───────────────────────┼──────────────────┼────────┤
│ orders       │ order_id = 123        │ created_at DESC  │  [×]   │
│ enriched     │ price > 10            │                  │  [×]   │
├──────────────┴───────────────────────┴──────────────────┴────────┤
│ [+ Add filter]                                                   │
└──────────────────────────────────────────────────────────────────┘
```

**Behavior:**
- Each row is **editable inline** — click the WHERE or ORDER BY cell to edit
- `[×]` removes that node's injection
- `[Clear All]` removes all injections
- `[+ Add filter]` shows a dropdown of all parsed nodes to pick from, creates a new row
- Right-click node → "Add filter" opens panel and creates/focuses a row for that node
- `[View effective SQL]` opens a read-only modal showing the full query with all injections applied

**No validation** — user types raw SQL fragments. If the injection produces invalid SQL, the error surfaces when the query executes. This keeps it simple and powerful (any valid SQL expression works).

### Storage

| Key | Value |
|-----|-------|
| sessionStorage key | `injections_{connection_id}` |
| Persistence | Survives page refresh, cleared on tab close |
| Stale entries | If a node ID no longer exists after re-parse (e.g., CTE renamed), its injection is silently dropped |

---

## 10. Graph Collapse & Focus

Three mechanisms to manage graph complexity:

### A. Collapsible Subtrees

Right-click a node with dependents → "Collapse subtree":

```
Before:
  raw_orders → orders → enriched → final_select
  products ──────────↗

After collapsing "enriched":
  [enriched +3] → final_select
```

- Children are hidden, replaced by a count badge `[+N]`
- Click the collapsed node or right-click → "Expand subtree" to reveal
- [Expand All] / [Collapse All] buttons in lineage toolbar

### B. "Show in Lineage" from Editor

Right-click a CTE/subquery name in the SQL editor → "Show in lineage":
- Opens lineage tab if closed
- Scrolls to and centers on that node
- **Dims all nodes outside its immediate neighborhood** (1 level up, 1 level down)
- Click anywhere on the graph background to un-dim

### C. Smart Default View

| Graph size | Default view |
|-----------|--------------|
| ≤ 12 nodes | Fully expanded |
| 13+ nodes | Root node + direct dependencies expanded. Other branches collapsed with count badges. |

User can expand any collapsed branch. [Expand All] to see everything.

### Standard Graph Interaction

- Zoom (scroll wheel)
- Pan (click + drag on background)

---

## 11. Results Viewer

Lives in the bottom drawer **[Results]** tab.

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ [orders ✓] [enriched ✓] [raw_orders ✗] [Full Query]    [Close] │
├─────────────────────────────────────────────────────────────────┤
│ Showing 847 of 847 rows │ 340ms │ Sort: price DESC            │
├────────────┬────────────┬──────────────┬───────────────────────┤
│ order_id ▲ │ product_id │ price ▼      │ status                │
├────────────┼────────────┼──────────────┼───────────────────────┤
│ 123        │ 456        │ 99.99        │ complete              │
│ 124        │ 789        │ 45.50        │ complete              │
│ ...        │            │              │                       │
├────────────┴────────────┴──────────────┴───────────────────────┤
│                                          [Copy CSV] [Copy JSON] │
└─────────────────────────────────────────────────────────────────┘
```

### Tab Types

| Tab | When Created |
|-----|-------------|
| Node name (e.g., "orders") | Execute-node (from lineage, editor gutter, or breakpoint) |
| "Full Query" | Click [Run ▶] on full query |

Each tab is independent — own sort, own filter, own scroll position.

### Features

| Feature | Behavior |
|---------|----------|
| Column sort | Click column header to toggle asc → desc → none |
| Column filter | Filter input per column (text match or numeric comparison) |
| Row count | "Showing X of Y rows". If truncated: "Showing 1,000 rows (query returned more)" |
| Execution time | Shown in metadata bar |
| Copy | [Copy CSV] and [Copy JSON] export full result or selected rows |
| Cell overflow | Long values truncated in table, click to expand in tooltip/popover |
| NULL display | `NULL` in muted italic grey style |

### Tab States

| State | Display |
|-------|---------|
| Loading | Spinner + "Executing..." |
| Success | Table with data |
| Error | Error message + database error detail + [Copy Error] |
| Cancelled | "Query cancelled" |
| Empty | "Query returned 0 rows" |

### Error Display

```
┌─────────────────────────────────────────┐
│ [orders ✗]                              │
├─────────────────────────────────────────┤
│                                         │
│  ❌ Query failed                        │
│                                         │
│  Column "order_idd" does not exist.     │
│  Hint: Perhaps you meant "order_id".    │
│                                         │
│  [Copy Error]                           │
│                                         │
└─────────────────────────────────────────┘
```

Database error messages passed through as-is (user's own DB, no security concern).

---

## 12. Tests

### Backend Tests

**Parse endpoint (20 tests):**

| # | Test |
|---|------|
| 1 | Simple CTE query → correct nodes and edges |
| 2 | Nested CTEs (CTE depends on CTE) → correct dependency chain |
| 3 | Subquery with alias → node type is "subquery", name is alias |
| 4 | Subquery without alias → node type is "subquery", name is truncated SQL |
| 5 | Table source → root node (in-degree 0), depends_on is empty |
| 6 | Multiple CTEs joining → correct fan-in edges |
| 7 | Precedence order matches SQL narrative order |
| 8 | Invalid SQL → 400 with error position |
| 9 | Empty SQL → 400 |
| 10 | Dialect-specific syntax (Snowflake, BigQuery) parses correctly |
| 11 | Table with alias (`products p`) → node name is table name, not alias |
| 12 | Postgres multi-part names: `orders`, `public.orders`, `"public"."orders"` → resolved to `schema.table` |
| 13 | MySQL multi-part names: `orders`, `mydb.orders`, backtick-quoted → resolved to `database.table` |
| 14 | BigQuery multi-part names: `orders`, `dataset.orders`, `project.dataset.orders`, backtick-quoted → resolved correctly |
| 15 | Snowflake multi-part names: `ORDERS`, `PUBLIC.ORDERS`, `PROD.PUBLIC.ORDERS` → resolved correctly |
| 16 | Self-join (`orders o1 JOIN orders o2`) → single table node with multiple outgoing edges |
| 17 | UNION/INTERSECT/EXCEPT branches within CTE → each branch is a separate subquery node |
| 18 | Subquery in WHERE (`WHERE id IN (SELECT ...)`) → parsed as subquery node |
| 19 | Recursive CTE (`WITH RECURSIVE`) → treated as regular CTE node |
| 20 | Dependency graph structure: edges, root nodes, sink nodes all correct for a complex multi-CTE query |

**Execute endpoint (8 tests):**

| # | Test |
|---|------|
| 21 | Simple query → returns columns + rows |
| 22 | Query with WHERE injection → filter applied via AST manipulation |
| 23 | Query with ORDER BY injection → order applied |
| 24 | Query with both WHERE and ORDER BY injection |
| 25 | Result capped at limit → truncated: true |
| 26 | Timeout exceeded → error response |
| 27 | Cancel mid-execution → cancelled response |
| 28 | Connection not found → 404 |

**Execute-node endpoint (12 tests):**

| # | Test |
|---|------|
| 29 | Single CTE, no dependencies → executes just that CTE |
| 30 | CTE with upstream dependency → reconstructed query includes dependency chain |
| 31 | Injection on target node → WHERE injected via AST (AND appended) |
| 32 | Injection on upstream dependency → injected into dependency, target gets filtered data |
| 33 | Injections on multiple nodes in chain → each node's SQL modified independently |
| 34 | Node with no WHERE clause + WHERE injection → WHERE clause added |
| 35 | Node with existing WHERE + WHERE injection → AND appended |
| 36 | ORDER BY injection → appended to node |
| 37 | Node ID not found in parse → 400 |
| 38 | No cached parse → 400 "Parse query first" |
| 39 | Table source node → executes SELECT * FROM table LIMIT N |
| 40 | Result limit and timeout applied |

**Effective-sql endpoint (5 tests):**

| # | Test |
|---|------|
| 41 | No injections → returns original SQL unchanged |
| 42 | Single injection → returns modified SQL |
| 43 | Multiple injections across chain → all applied |
| 44 | Invalid injection (bad SQL fragment) → returns SQL as-is |
| 45 | Empty injections map → returns original SQL |

**Cancel endpoint (3 tests):**

| # | Test |
|---|------|
| 46 | Cancel running query → query terminated, execute returns cancelled |
| 47 | Cancel with unknown request_id → 404 |
| 48 | Cancel already-completed query → no-op, success |

### Frontend Tests

**SQL Editor (8 tests):**

| # | Test |
|---|------|
| 49 | Paste SQL → editor content updates |
| 50 | Upload .sql → editor content replaced |
| 51 | Right-click CTE name → context menu with "Show in lineage" |
| 52 | Syntax highlighting active |
| 53 | Background re-parse fires 300ms after typing stops |
| 54 | Re-parse failure (invalid SQL) → uses last known good parse |
| 55 | Hover recognized span → background highlight + gutter ▶ appears |
| 56 | Overlapping spans → right-click shows options for all enclosing nodes |

**Action Bar (7 tests):**

| # | Test |
|---|------|
| 57 | [Visualize] calls parse endpoint, opens lineage tab |
| 58 | [Run ▶] calls execute with current SQL + injections |
| 59 | [Run ▶] disabled when no active connection |
| 60 | [Upload .sql] opens file picker, replaces editor content |
| 61 | [Cancel] visible during execution, hidden otherwise |
| 62 | [Cancel] sends cancel request for all active executions |
| 63 | Buttons disabled during their respective operations (spinner shown) |

**Editor Inline Execution (10 tests):**

| # | Test |
|---|------|
| 64 | Hover CTE → span highlighted, ▶ appears in gutter |
| 65 | Hover subquery → span highlighted, ▶ appears |
| 66 | Hover table name → span highlighted, ▶ appears |
| 67 | Click ▶ on CTE → executes subtree with injections |
| 68 | Click ▶ on table → executes preview query (SELECT * LIMIT 1000) |
| 69 | Overlapping spans → innermost node selected by default |
| 70 | No gutter buttons before first parse completes |
| 71 | Right-click ▶ → context menu with all node actions |
| 72 | Hover CTE in editor → execute from gutter → result appears in Results tab |
| 73 | Hover node in editor → right-click → add filter → filter panel opens with row for that node |

**Bidirectional Sync (5 tests):**

| # | Test |
|---|------|
| 74 | Click lineage node → corresponding SQL span highlighted in editor |
| 75 | Click SQL span in editor → matching lineage node highlighted |
| 76 | Edit SQL → 300ms debounce → positions update → sync remains accurate |
| 77 | Background re-parse timing: parse completes within acceptable time for graph rendering |
| 78 | Re-parse failure → node execution disabled with message |

**Lineage Graph (18 tests):**

| # | Test |
|---|------|
| 79 | Graph renders correct nodes and edges from parse result |
| 80 | Dependency mode shows data flow direction (sources at top/left) |
| 81 | Precedence mode shows narrative order |
| 82 | Toggle between dependency and precedence mode works |
| 83 | Click node → highlights SQL span in editor |
| 84 | Double-click node → executes node, result in Results tab |
| 85 | Right-click → context menu with all options |
| 86 | Collapse subtree → children hidden, badge shows count |
| 87 | Expand subtree → children visible |
| 88 | Smart default: ≤12 nodes fully expanded |
| 89 | Smart default: 13+ nodes auto-collapsed |
| 90 | [Expand All] / [Collapse All] work |
| 91 | Staleness banner appears when SQL edited since last [Visualize] |
| 92 | "Show in lineage" from editor → scrolls to node, dims distant nodes |
| 93 | Click graph background → un-dims all nodes |
| 94 | Hover node → highlights node + direct edges |
| 95 | Nodes color-coded by type (Blue=CTE, Purple=Subquery, Green=Table) |
| 96 | Hover node → tooltip shows type label ("CTE: orders", "Table: public.orders") |

**Breakpoints (15 tests):**

| # | Test |
|---|------|
| 97 | Toggle breakpoint on node → indicator changes |
| 98 | Breakpoint upstream → all ancestors breakpointed |
| 99 | Breakpoint downstream → all dependents breakpointed |
| 100 | Type filter: toggle off "Tables" → table source breakpoints removed |
| 101 | Type filter: toggle back on → re-added |
| 102 | Manual select/deselect after type filter works |
| 103 | [Run Breakpoints] executes all breakpointed nodes in parallel |
| 104 | Results shown only after all breakpoint queries complete |
| 105 | First result tab shown, [Next] advances to next in order |
| 106 | [Show All] reveals all tabs at once |
| 107 | Tab order matches graph mode (dependency order / precedence order) |
| 108 | [Clear Breakpoints] removes all |
| 109 | Cancel during breakpoint execution cancels all running queries |
| 110 | Node status indicators update correctly (⟳ → ✓ or ✗) |
| 111 | Each breakpoint result appears in its own tab |

**Filter & Order Panel (9 tests):**

| # | Test |
|---|------|
| 112 | Injection status bar shows count of active filters |
| 113 | Click status bar toggles filter panel |
| 114 | Right-click node → "Add filter" opens panel with new row |
| 115 | Edit WHERE inline → injection updated |
| 116 | Edit ORDER BY inline → injection updated |
| 117 | [×] removes injection for that node |
| 118 | [Clear All] removes all injections |
| 119 | [View effective SQL] shows modal with modified query |
| 120 | Filters persist in sessionStorage across page refresh |

**Results Viewer (12 tests):**

| # | Test |
|---|------|
| 121 | Full query result displayed in table |
| 122 | Node execution result displayed in named tab |
| 123 | Breakpoint results shown in separate tabs |
| 124 | Per-tab independent sort (click column header) |
| 125 | Per-tab independent column filter |
| 126 | Row count shows "Showing X of Y rows" |
| 127 | Truncated results show "(query returned more)" message |
| 128 | NULL values displayed in muted italic style |
| 129 | Long cell values truncated, click to expand |
| 130 | [Copy CSV] / [Copy JSON] exports current tab data |
| 131 | Error result shows error message + [Copy Error] |
| 132 | Empty result shows "Query returned 0 rows" |

### Summary: 132 tests (48 backend + 84 frontend)

---

## 13. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Parse location | Local backend (Python/sqlglot) | Single parser, local backend always running |
| Result row limit | 1,000 default | Enough for debugging, fast to transfer/render |
| Query timeout | 60s default, configurable per request | Generous for BigQuery/Snowflake, user can adjust |
| Execute-node model | Backend uses cached parse, frontend sends node_id only | Single source of truth for parsing, no redundant SQL transfer |
| Injection method | sqlglot AST manipulation (AND into WHERE, not subquery wrapping) | Correct for columns not in SELECT list, more efficient |
| Breakpoint execution | All in parallel, wait for all, then show with Next/Show All | Fast execution, guided navigation for many results |
| Breakpoint order | Dependency order in dependency graph, narrative order in precedence graph | Matches the active graph mode |
| Subtree selection | User chooses upstream or downstream, with type filter + manual adjust | Flexible for complex queries |
| Graph collapse | Collapsible subtrees + show-in-lineage focus + smart default (≤12 expanded) | Three mechanisms for different needs |
| Editor inline execution | Hover to highlight + gutter ▶, works for all node types | Fast debugging without lineage detour |
| Overlapping spans | Innermost node by default, right-click for enclosing nodes | Natural, power users get full access |
| Filter storage | sessionStorage (survives refresh, cleared on tab close) | Filters are session-specific, not persistent |
| Filter validation | None — raw SQL fragments | Simple, powerful, errors surface on execute |
| Cancel execution | Frontend-generated request_id, backend kills cursor | Simple cancellation model |
| Effective SQL endpoint | Named `/query/effective-sql` (not `/query/preview`) | Clear naming, avoids confusion with data preview |
| Results viewer | Included in this spec (not separate) | Integral to query console flow |
| Error messages | Pass through database errors as-is | User's own DB, no security concern |
| NULL display | Muted italic grey `NULL` | Visually distinct from empty string |
| Node IDs | No type prefix — SQL prevents CTE/table collisions. Subquery uses parent scope. | Clean IDs, no artificial prefixes |
| Node visual differentiation | Color-coded by type (Blue/Purple/Green) + type label on hover | Keeps nodes uncluttered, type visible at a glance |
| Table aliases | Show table name, not alias. `products p` displays as `products`. | Table identity is the name, alias is SQL convenience |
| Same table multiple refs | One node with multiple outgoing edges | Single data source, multiple consumers |
| UNION/EXCEPT branches | Each branch is a separate subquery node | Lets users execute/debug each branch independently |
| Recursive CTEs | Treated as regular CTE node | No special handling in MVP |
| Subqueries in WHERE | Treated as subquery nodes | They reference tables and can be executed independently |
| Table sources | Root nodes (in-degree 0), not leaf nodes | Data flows FROM sources, not TO them |

---

## Frontend Component Structure

```
QueryConsole (top-level)
├── SqlEditor
│   ├── Monaco/CodeMirror wrapper
│   ├── Gutter run buttons (▶ on hover)
│   └── Context menu ("Show in lineage", "Execute", "Add filter")
├── ActionBar
│   ├── [Visualize] [Run ▶] [Upload .sql]
│   └── [Cancel] (visible during execution)
├── InjectionStatusBar ("⚡ 2 filters active" + [View effective SQL])
├── FilterOrderPanel (toggleable)
│   ├── Injection table (Node | WHERE | ORDER BY | [×])
│   └── [+ Add filter] [Clear All]
│
└── BottomDrawer (collapsible)
    ├── [Lineage] tab
    │   ├── LineageToolbar
    │   │   ├── GraphModeToggle
    │   │   ├── BreakpointTypeFilter
    │   │   ├── [Run Breakpoints] [Clear Breakpoints]
    │   │   └── [Expand All] [Collapse All]
    │   ├── StalenessBanner
    │   └── LineageGraph
    │       └── LineageNode (per node)
    │           ├── Status indicator (○/●/✓/✗/⟳)
    │           ├── Type label + name
    │           ├── Quick execute [▶] + filter indicator ⊘
    │           ├── Collapse badge [+N]
    │           └── Context menu
    │
    └── [Results] tab
        ├── ResultTabBar (node tabs + "Full Query")
        └── ResultPanel (per tab, independent state)
            ├── ResultMetaBar (row count, time, sort info)
            ├── ResultTable (sortable, filterable columns)
            ├── ResultError / ResultEmpty / ResultCancelled
            └── ResultActions ([Copy CSV] [Copy JSON])
```

### Key State

```
// Editor
sql: string                              // current editor content

// Parse
parseResult: ParseResult | null          // latest background re-parse (data truth)
visualGraph: ParseResult | null          // last explicit [Visualize] (rendered graph)
isGraphStale: boolean                    // sql changed since last [Visualize]

// Graph interaction
collapsedNodes: Set<nodeId>              // subtrees collapsed
dimmedNodes: Set<nodeId>                 // nodes dimmed (outside focus)
graphMode: "dependency" | "precedence"

// Breakpoints
breakpoints: Set<nodeId>
breakpointTypeFilter: {
  ctes: boolean,
  tables: boolean,
  subqueries: boolean
}

// Injections (persisted in sessionStorage)
injections: Map<nodeId, {
  where?: string,
  order_by?: string
}>

// Execution
executionResults: Map<nodeId | "full", ExecutionResult>
activeExecutions: Map<requestId, nodeId>   // for cancellation
activeResultTab: string

// Config
resultLimit: number                        // default 1000
queryTimeout: number                       // default 60
```

---

## Related Documents

- `04-query-console-design.md` — High-level design (this spec expands it)
- `01-connection-management-frontend-v2.md` — Connection management
- `02-connection-management-backend-v2.md` — Backend architecture, storage
- `03-schema-browser-frontend.md` — Schema browser

---

*End of Query Console, Lineage & Results Detailed Spec*
