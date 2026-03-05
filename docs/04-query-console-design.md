# Query Console & Lineage — Design

## Document Info

| Item | Value |
|------|-------|
| Feature | Query Console, Lineage Visualization, Bidirectional Sync |
| Status | Agreed |
| Date | March 2026 |

---

## 1. Overall Application Layout

The application is structured as a four-panel IDE, inspired by PyCharm's layout. All panel splits are draggable and resizable.

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
│             ├──────────────────────────────────┤           │
│             │ [Lineage]  [Results]              │           │
│             │  (bottom drawer — collapsible)    │           │
└─────────────┴──────────────────────────────────┴───────────┘
```

| Panel | Position | Default State |
|-------|----------|---------------|
| Schema Browser | Left | Hidden, toggleable |
| Query Console | Center | Always visible |
| AI Chat | Right | Collapsed, toggleable |
| Bottom Drawer | Bottom | Collapsed, toggleable |

The bottom drawer contains two tabs: **[Lineage]** and **[Results]**.

---

## 2. Query Console

### Editor

- SQL editor with syntax highlighting (Monaco or CodeMirror)
- Accepts paste directly or file upload via [Upload .sql]
- The editor always shows the **original SQL as the user wrote it** — injected filters/orders are never shown in the editor

### Actions

| Button | Behavior |
|--------|----------|
| [Visualize] | Parses SQL locally (sqlglot, no DB call). Opens bottom drawer to Lineage tab. Works without a DB connection. |
| [Run ▶] | Builds the effective query (original SQL + active injections), executes against DB. Opens bottom drawer to Results tab. |
| [Upload .sql] | File picker, replaces current editor content. |

### Injection Status Bar

When filters or ORDER BY injections are active on any node, a status bar below the editor shows:

```
⚡ 2 filters active
```

Clicking this indicator opens a read-only preview modal showing the effective query (what will actually execute). No query history in MVP.

---

## 3. Lineage Tab

### Two Graph Modes

The lineage panel has a toggle between two graph modes:

| Mode | Description | Default |
|------|-------------|---------|
| **Dependency graph** | DAG showing data flow — what each node depends on to run. Table sources are leaf nodes. Used for debugging and node execution. | ✅ Yes |
| **Precedence graph** | Nodes ordered by their position in the SQL as written. Shows the query's narrative structure. | No |

### Node Types

| Type | Name shown | Example |
|------|-----------|---------|
| CTE | Declared name | `orders`, `enriched` |
| Subquery with alias | The alias | `t1`, `filtered_base` |
| Subquery without alias | Truncated SQL snippet | `SELECT id, price FR…` |
| Table source (leaf) | `schema.table` | `public.raw_orders` |

### Node Interactions

- **Click a node** → scrolls to and highlights the corresponding SQL span in the console editor
- **Execute a node** → reconstructs the node's full query subtree (node + all upstream dependencies from the dependency graph), applies per-node injections for each included node, executes against DB, shows results in the Results tab
- **Set breakpoint on a node** → marks it; user can set multiple breakpoints and step through them sequentially, one execution per step

### Staleness Banner

When the query in the console has been edited since the last [Visualize] click, the lineage panel shows:

```
⚠ Graph outdated — click Visualize to refresh
```

This is a visual warning only. The underlying parse data (positions, node SQL, dependencies) is kept fresh by the background re-parse (see Section 5).

---

## 4. Schema Browser

- Tree view: connection → schema → table → columns with data types
- Search/filter box at top for large schemas
- Blocked tables shown grayed out (from connection ACL)
- **Click a table** → no action in MVP (future: insert into console)
- **Click a column** → no action in MVP
- No drag-and-drop in MVP

---

## 5. Bidirectional Sync: Console ↔ Lineage

### Two directions

| Direction | Trigger | Effect |
|-----------|---------|--------|
| Lineage → Console | Click a lineage node | Scrolls to and highlights the corresponding SQL span in the editor |
| Console → Lineage | Click or select a SQL span in the editor | Highlights the matching lineage node |

### Background Re-parse

The key mechanism keeping sync accurate as the user edits:

- **Visual graph** (rendered nodes/edges in Lineage tab): only updates when user explicitly clicks [Visualize]. Stable, user-controlled.
- **Parse data** (source positions, node SQL, dependency graph): re-parsed silently in the background, 300ms after the user stops typing. No visual change to the lineage graph.

This means:
- Source positions stay accurate as the user edits → highlight sync remains correct
- Node SQL stays current → executing a node from the lineage always uses the current editor content, not a stale snapshot
- Dependency graph stays current → correct upstream CTEs are included in node execution

**The visual graph can be stale. The data underneath never is.**

### Failure handling

If the background re-parse fails (SQL is mid-edit and syntactically invalid):
- Use last known good positions for highlight sync
- Disable node execution from the lineage with message: *"Query has changed and can't be parsed — fix syntax or click Visualize to refresh"*

### Edge case

If the user edits and clicks a node within the 300ms debounce window (before re-parse fires), the last known positions are used. The highlight may be slightly off. Acceptable for MVP.

---

## 6. Filter & Order Injection

### Model

- Injections are stored **client-side only** — never persisted server-side
- Each injection is per-node: an optional WHERE clause and/or ORDER BY clause
- Passed with every execute call (node execution or full query run)

### Execution behavior

When running a node, the backend:
1. Walks the dependency graph upward from the target node to collect all ancestor CTEs
2. Applies each node's injections via sqlglot AST manipulation (WHERE appended with AND, ORDER BY appended)
3. Builds the full reconstructed query
4. Executes and returns results (capped)

Injection pattern:
```sql
-- Original CTE:
orders AS (SELECT * FROM raw_orders WHERE status = 'complete')

-- After injecting WHERE order_id = 123:
orders AS (
  SELECT * FROM raw_orders
  WHERE status = 'complete' AND order_id = 123
)
```

---

## 7. Backend Services Required

| Endpoint | Purpose | DB call? |
|----------|---------|----------|
| `POST /query/parse` | Parse SQL → lineage graph (nodes, edges, source positions, node SQL). Called by [Visualize] and background re-parse. | No |
| `POST /connections/{id}/execute` | Execute full query with all active injections. | Yes |
| `POST /connections/{id}/execute-node` | Execute a specific node's subtree with dependency + per-node injections. | Yes |
| `POST /query/effective-sql` | Return effective query string (original + injections applied). No execution. | No |

### Parse response structure (per node)

```json
{
  "id": "orders",
  "type": "cte",
  "name": "orders",
  "sql": "SELECT * FROM raw_orders WHERE status = 'complete'",
  "source_position": {
    "start_line": 2,
    "start_char": 10,
    "end_line": 4,
    "end_char": 5
  },
  "depends_on": []
}
```

---

## 8. What This Design Defers

| Topic | Deferred to |
|-------|-------------|
| Detailed query console, lineage, and results spec | `05-query-console-lineage-detailed.md` |
| AI Chat and agentic debugging spec | `06-ai-chat-and-debugging.md` |
| Schema Browser full spec | `03-schema-browser-frontend.md` |

---

*End of Query Console & Lineage Design*
