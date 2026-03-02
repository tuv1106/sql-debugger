# Connection Management — Backend Spec

## Document Info

| Item | Value |
|------|-------|
| Feature | Connection Management |
| Layer | Backend (Local) |
| Status | Agreed |
| Date | February 2026 |
| Version | 2.0 — Hierarchical entity exclusion (replaces flat table blocking) |

---

## 1. Overview

Local backend handles all database operations. Runs on user's machine, stores credentials securely, executes queries. Cloud backend never sees credentials or query results.

**Key principles:**
- Stateless requests — each request includes `connection_id`
- Active connection managed by UI (localStorage), not backend
- Passwords in keyring, metadata in config.json
- Entity exclusions denormalized for O(1) reads

---

## 2. Project Structure

```
local_backend/
├── main.py                     # FastAPI app, startup reconciliation
├── api/
│   └── connections.py          # Route handlers
├── models/
│   ├── common.py               # Shared response models
│   ├── connection.py           # ConnectionParams (base + per DB type)
│   ├── entities.py             # EntityIdentifier, ExclusionConfig (base + per DB type)
│   └── tables.py               # TableIdentifier (base + per DB type)
├── services/
│   └── connection_service.py   # Business logic
├── db/
│   ├── base.py                 # Abstract DatabaseAdapter
│   ├── postgres.py / mysql.py / bigquery.py / snowflake.py
├── storage/
│   └── config_store.py         # Config.json + keyring operations
└── errors/
    └── exceptions.py           # Custom exceptions
```

---

## 3. Components

### 3.1 Connection Parameters

**Base:** `ConnectionParams` with `name`, `db_type`, `validate()`

| Subclass | Fields |
|----------|--------|
| PostgresConnectionParams | host, port, database, username, password |
| MySQLConnectionParams | host, port, database, username, password |
| BigQueryConnectionParams | project_id, dataset, service_account_json |
| SnowflakeConnectionParams | account, warehouse, database, schema, username, password |

**Validation:** On create/update/test only, NOT when loading from config.

---

### 3.2 Table Identifiers

**Base:** `TableIdentifier` with `full_name()`, `to_dict()`, `from_dict()`

| Subclass | full_name() output |
|----------|-------------------|
| PostgresTable | "schema.table" |
| MySQLTable | "database.table" |
| BigQueryTable | "project.dataset.table" |
| SnowflakeTable | "database.schema.table" |

---

### 3.3 Entity Exclusion Model

**Per DB type — excludable levels and storage keys:**

| DB | Excludable Levels | Storage Keys |
|----|-------------------|-------------|
| Postgres | schema, table | `blocked_schemas`, `blocked_tables` |
| MySQL | database, table | `blocked_databases`, `blocked_tables` |
| BigQuery | dataset, table | `blocked_datasets`, `blocked_tables` |
| Snowflake | database, schema, table | `blocked_databases`, `blocked_schemas`, `blocked_tables` |

**Not excludable (= the connection itself):** Postgres database, BigQuery project.

**`ExclusionConfig` base class:**
- `is_excluded(entity) -> bool` — O(1) check
- `exclude_entity(entity)` — adds to appropriate storage, denormalizes
- `include_entity(entity)` — removes, handles parent demotion
- `exclude_all(schema_tree)` — bulk exclude
- `include_all()` — clear all
- `sync_new_tables(schema_tree)` — add new tables under excluded parents

**Subclasses:** `PostgresExclusionConfig`, `MySQLExclusionConfig`, `BigQueryExclusionConfig`, `SnowflakeExclusionConfig`

**Resolution logic for `is_excluded(table)`:**

```
1. table in blocked_tables[parent_key]? → excluded
2. parent in blocked_schemas/blocked_databases/blocked_datasets? → excluded
3. default → included
```

**Operations and storage changes:**

| Action | Storage Change |
|--------|----------------|
| Exclude schema X | Add X to `blocked_schemas`. Add ALL current tables under X to `blocked_tables[X]` |
| Include table X.foo (X is excluded) | Remove foo from `blocked_tables[X]`. Remove X from `blocked_schemas`. Others stay in `blocked_tables[X]` individually |
| Include schema X | Remove X from `blocked_schemas`. Remove `blocked_tables[X]` entirely |
| Exclude table X.foo | Add foo to `blocked_tables[X]`. Do NOT auto-promote schema to `blocked_schemas` |
| Exclude All | Add all top-level entities to blocked list. Add all tables to `blocked_tables` |
| Include All | Clear `blocked_schemas`, `blocked_databases`, `blocked_datasets`, `blocked_tables` |
| Schema refresh (sync) | For each entity in `blocked_schemas`/`blocked_databases`: add any new discovered tables to `blocked_tables` |

**Key rule — no auto-promotion:**
- `blocked_schemas` only contains schemas the user **explicitly** excluded at schema level
- Individually excluding all tables in a schema does NOT add the schema to `blocked_schemas`
- New table in explicitly-excluded schema → auto-added to `blocked_tables` (inherited)
- New table in schema where all tables individually excluded → NOT excluded

---

### 3.4 Config Store

**Location:** `~/.sql-debugger/config.json`

**Keyring:** service `sql-debugger`, key = `connection_id`

**Methods:**
- `save_connection(id, params)` — writes config + keyring
- `load_connection(id)` — merges both, raises `NeedsReauthError` if password missing
- `delete_connection(id)` — removes from both
- `list_connections()` — summaries without passwords
- `find_by_name_and_type(name, db_type)` — for duplicate check
- `save_exclusions(id, exclusion_config)` — writes exclusion data to config
- `load_exclusions(id)` — returns ExclusionConfig
- `reconcile()` — startup sync (orphan passwords, missing passwords)

---

### 3.5 Database Adapter

**Abstract interface:**
- `test_connection(timeout) -> bool`
- `list_entities() -> EntityTree` — returns hierarchical structure (schemas/databases → tables)
- `get_schema() -> Dict[table, List[ColumnInfo]]`
- `execute(query, limit, timeout) -> QueryResult`

**Factory:** `get_adapter(params)` returns correct adapter for db_type

**`EntityTree` structure** (returned by `list_entities()`):
```python
# Postgres example
{
  "schemas": {
    "public": ["orders", "products", "users"],
    "sensitive": ["audit_log", "tokens"]
  }
}

# Snowflake example
{
  "databases": {
    "prod": {
      "public": ["orders", "products"],
      "pii_schema": ["users", "cards"]
    },
    "staging": {
      "public": ["test_orders"]
    }
  }
}
```

---

### 3.6 Connection Service

Business logic layer. Key methods:
- `create_connection` — generates UUID, checks duplicate, saves
- `update_connection` — checks duplicate if name changed
- `delete_connection`
- `test_connection` — accepts params or connection_id
- `list_entities` — returns entity tree with exclusion status merged
- `exclude_entities(connection_id, entities)` — validates entity types, delegates to ExclusionConfig
- `include_entities(connection_id, entities)` — validates entity types, delegates to ExclusionConfig
- `exclude_all(connection_id)` — fetches entity tree, excludes all
- `include_all(connection_id)` — clears all exclusions

**Entity type validation:** Service checks that requested entity levels match the DB type's excludable levels. Requesting to exclude a "schema" on MySQL → `ValidationError`.

---

### 3.7 Errors

| Error | Contains |
|-------|----------|
| ConnectionNotFoundError | connection_id |
| DuplicateConnectionError | name, db_type |
| NeedsReauthError | connection_id |
| ConfigCorruptedError | file_path |
| KeyringAccessError | operation, platform |
| KeyringWriteError | connection_id |
| ValidationError | field, message |
| InvalidEntityLevelError | level, db_type, allowed_levels |

---

## 4. Storage Format

**config.json — Postgres connection example:**
```json
{
  "version": "2.0",
  "connections": {
    "<uuid>": {
      "name": "Production Postgres",
      "db_type": "postgres",
      "host": "prod.rds.amazonaws.com",
      "port": 5432,
      "database": "myapp",
      "username": "admin",
      "needs_reauth": false,
      "blocked_schemas": ["sensitive", "pii"],
      "blocked_tables": {
        "sensitive": ["users", "payments", "audit_log"],
        "pii": ["customers", "addresses"],
        "public": ["internal_config"]
      }
    }
  }
}
```

**config.json — MySQL connection example:**
```json
{
  "version": "2.0",
  "connections": {
    "<uuid>": {
      "name": "Production MySQL",
      "db_type": "mysql",
      "host": "prod-db.rds.amazonaws.com",
      "port": 3306,
      "database": "myapp",
      "username": "admin",
      "needs_reauth": false,
      "blocked_databases": ["secret_db"],
      "blocked_tables": {
        "secret_db": ["users", "tokens"],
        "myapp": ["internal_config"]
      }
    }
  }
}
```

**config.json — BigQuery connection example:**
```json
{
  "version": "2.0",
  "connections": {
    "<uuid>": {
      "name": "BigQuery Analytics",
      "db_type": "bigquery",
      "project_id": "project-123",
      "dataset": "analytics",
      "needs_reauth": false,
      "blocked_datasets": ["raw_pii"],
      "blocked_tables": {
        "raw_pii": ["customers", "addresses", "phone_numbers"],
        "analytics": ["internal_revenue"]
      }
    }
  }
}
```

**config.json — Snowflake connection example:**
```json
{
  "version": "2.0",
  "connections": {
    "<uuid>": {
      "name": "Snowflake Prod",
      "db_type": "snowflake",
      "account": "xy12345.us-east-1",
      "warehouse": "COMPUTE_WH",
      "database": "PROD",
      "schema": "PUBLIC",
      "username": "admin",
      "needs_reauth": false,
      "blocked_databases": ["SECRETS_DB"],
      "blocked_schemas": ["PROD.PII_SCHEMA"],
      "blocked_tables": {
        "SECRETS_DB.PUBLIC": ["TOKENS", "API_KEYS"],
        "SECRETS_DB.INTERNAL": ["CREDS"],
        "PROD.PII_SCHEMA": ["USERS", "CARDS"],
        "PROD.PUBLIC": ["INTERNAL_CONFIG"]
      }
    }
  }
}
```

**Keyring:** `{connection_id}` → password string (or JSON for BigQuery)

---

## 5. API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | /health | Health check |
| GET | /connections | List all |
| POST | /connections | Create |
| GET | /connections/{id} | Get one |
| PUT | /connections/{id} | Update |
| DELETE | /connections/{id} | Delete |
| POST | /connections/test | Test connection |
| GET | /connections/{id}/entities | List entity tree with exclusion status |
| POST | /connections/{id}/entities/exclude | Exclude entities |
| POST | /connections/{id}/entities/include | Include entities |
| POST | /connections/{id}/entities/exclude-all | Exclude all |
| POST | /connections/{id}/entities/include-all | Include all |

---

## 6. Tests

### Unit Tests

**Connection Params (7 tests):**
- Valid/invalid params per DB type
- Missing required fields → ValidationError

**Table Identifiers (7 tests):**
- full_name() returns correct format
- Serialization/deserialization roundtrip

**Entity Exclusion Config (24 tests):**
- `is_excluded` — direct table exclusion returns true
- `is_excluded` — inherited from parent returns true
- `is_excluded` — non-excluded table returns false
- `exclude_entity` schema — adds to blocked_schemas + all tables to blocked_tables
- `exclude_entity` table — adds only to blocked_tables, NOT to blocked_schemas
- `include_entity` table under excluded schema — removes table, removes schema from blocked_schemas, siblings stay
- `include_entity` schema — removes schema + all its entries from blocked_tables
- `exclude_all` — all levels populated
- `include_all` — all levels cleared
- No auto-promotion — all tables individually excluded, schema NOT in blocked_schemas
- New table in explicitly-excluded schema → excluded after sync
- New table in non-excluded schema (all tables individually excluded) → NOT excluded after sync
- `sync_new_tables` adds new tables under excluded parents only
- Per DB type: Postgres (schema, table), MySQL (database, table), BigQuery (dataset, table), Snowflake (database, schema, table)
- InvalidEntityLevelError when excluding wrong level for DB type
- Serialization/deserialization roundtrip for each DB type

**Config Store (20 tests):**
- Save writes config + keyring
- Password never in config.json
- Load merges config + keyring
- Missing password → NeedsReauthError
- Missing config → ConnectionNotFoundError
- Corrupted config → ConfigCorruptedError
- Keyring failures → appropriate errors
- Reconcile handles orphans and missing passwords
- save_exclusions writes correct structure per DB type
- load_exclusions returns correct ExclusionConfig subclass

**Connection Service (16 tests):**
- Create generates UUID
- Duplicate name+type → DuplicateConnectionError
- Same name different type → OK
- Test with valid/invalid/timeout params
- list_entities merges entity tree with exclusion status
- exclude_entities validates entity levels against DB type
- exclude_entities with invalid level → InvalidEntityLevelError
- include_entities handles parent demotion correctly

**Errors (7 tests):**
- Each error exposes expected fields
- InvalidEntityLevelError includes level, db_type, allowed_levels

### Integration Tests

**API (24 tests):**
- Health check returns 200
- Full CRUD flow works
- Duplicate returns 400
- Not found returns 404
- Password never in response
- GET /entities returns correct tree structure
- POST /entities/exclude excludes schema + denormalizes tables
- POST /entities/include on single table demotes parent
- POST /entities/exclude-all excludes everything
- POST /entities/include-all clears everything
- Invalid entity level returns 400

**Full Flows (5 tests):**
- Create → test → save → list → delete
- Create → exclude schema → verify status → include one table → verify demotion
- Create → exclude all → include all → verify clean
- Missing keyring → needs_reauth flow
- Schema refresh with excluded parent → new tables auto-excluded

### DB Adapter Tests (Docker)

**Per adapter (16 tests total):**
- Connect valid/invalid credentials
- Timeout handling
- list_entities returns correct hierarchy per DB type
- List tables, execute queries

### Summary: 126 tests total

---

## 7. Tech Stack

| Component | Library |
|-----------|---------|
| Framework | FastAPI |
| Validation | Pydantic |
| Postgres | psycopg2-binary |
| MySQL | mysql-connector-python |
| BigQuery | google-cloud-bigquery |
| Snowflake | snowflake-connector-python |
| Secrets | keyring |
| Testing | pytest |
| Test DBs | Docker |

---

## 8. Startup

On startup, call `config_store.reconcile()`:
1. Remove orphan keyring entries (no matching config)
2. Mark connections with missing passwords as `needs_reauth: true`

---

## 9. Related Documents

- `01-connection-management-frontend.md` (v2)
- `03-schema-browser-frontend.md`
- `00-project-overview.md`

---

*End of Connection Management Backend Spec v2*
