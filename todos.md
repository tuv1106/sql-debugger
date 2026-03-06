# SQL Debugger — Task Tracker

> **Task details:** See `docs/plans/2026-03-05-implementation-plan.md` for Purpose, Context, Files, Tests, and Spec references per task.

---

## Phase 1: Scaffolding

- [x] 1.1: Local Backend Project Setup | branch: `feat/1.1-local-backend-setup` | commit: `73a397a`
- [ ] 1.2: Frontend Project Setup | branch: | commit:
- [x] 1.3: Cloud Backend Project Setup | branch: `feat/1.1-local-backend-setup` | commit:
- [ ] 1.4: Docker Compose for Development | branch: | commit:

## Phase 2: Local Backend — Connection Management

> Depends on: Phase 1 complete

- [ ] 2.1: Connection Models (Pydantic) | branch: | commit:
- [ ] 2.2: Table Identifiers | branch: | commit:
- [ ] 2.3: Entity Exclusion Model | branch: | commit:
- [ ] 2.4: Config Store | branch: | commit:
- [ ] 2.5: Custom Exceptions | branch: | commit:
- [ ] 2.6: Database Adapters — Abstract + Postgres | branch: | commit:
- [ ] 2.7: Database Adapters — MySQL | branch: | commit:
- [ ] 2.8: Database Adapters — BigQuery | branch: | commit:
- [ ] 2.9: Connection Service | branch: | commit:
- [ ] 2.10a: Connection CRUD & Health API | branch: | commit:
- [ ] 2.10b: Connection Lifecycle API | branch: | commit:
- [ ] 2.10c: Entity & Exclusion API | branch: | commit:

## Phase 3: Frontend — Connection Management

> Depends on: Phase 2 complete

- [ ] 3.1: API Client Module | branch: | commit:
- [ ] 3.2: Connection Store (Zustand) | branch: | commit:
- [ ] 3.3: Connection Icon & Panel | branch: | commit:
- [ ] 3.4: Connection Form Modal | branch: | commit:
- [ ] 3.5: Delete Confirmation & Local Backend Warning | branch: | commit:

## Phase 4: Local Backend — Schema & Query Endpoints

> Depends on: Phase 1 complete (can run in parallel with Phase 2)

- [ ] 4.1: SQL Parser Service (sqlglot) | branch: | commit:
- [ ] 4.2: Query Execution Service | branch: | commit:
- [ ] 4.3: Execute-Node & Effective SQL | branch: | commit:
- [ ] 4.4: Query API Endpoints | branch: | commit:

## Phase 5: Frontend — Schema Browser

> Depends on: Phase 3 and Phase 4 complete

- [ ] 5.1: Schema Store & Cache | branch: | commit:
- [ ] 5.2a: Schema Tree Rendering | branch: | commit:
- [ ] 5.2b: Panel States, Search & Footer | branch: | commit:
- [ ] 5.2c: Cache & Refresh Integration | branch: | commit:

## Phase 6: Frontend — Query Console

> Depends on: Phase 5 complete

- [ ] 6.1a: SQL Editor Core (CodeMirror 6) | branch: | commit:
- [ ] 6.1b: Gutter Buttons & Inline Execution | branch: | commit:
- [ ] 6.2: Action Bar & File Upload | branch: | commit:
- [ ] 6.3: Parse & Execution Stores | branch: | commit:

## Phase 7: Frontend — Lineage Visualization

> Depends on: Phase 6 complete

- [ ] 7.1: React Flow + ELK Layout | branch: | commit:
- [ ] 7.2: Lineage Nodes | branch: | commit:
- [ ] 7.3: Lineage Toolbar & Graph Modes | branch: | commit:
- [ ] 7.4: Breakpoints | branch: | commit:
- [ ] 7.5: Bidirectional Sync | branch: | commit:
- [ ] 7.6: Graph Collapse & Focus | branch: | commit:

## Phase 8: Frontend — Results Viewer & Injection

> Depends on: Phase 7 complete

- [ ] 8.1: Results Viewer | branch: | commit:
- [ ] 8.2: Filter & Order Injection Panel | branch: | commit:

## Phase 9: Local Backend — AI Support Endpoints

> Depends on: Phase 8 complete (can run in parallel with Phase 10)

- [ ] 9.1: Table Profile Endpoint | branch: | commit:
- [ ] 9.2: Indexes Endpoint | branch: | commit:
- [ ] 9.3: Sample Endpoint | branch: | commit:

## Phase 10: Cloud Backend

> Depends on: Phase 8 complete (can run in parallel with Phase 9)

- [ ] 10.1: Session Management | branch: | commit:
- [ ] 10.2: SSE Streaming & Event Registry | branch: | commit:
- [ ] 10.3: Chat & Debug API Endpoints | branch: | commit:
- [ ] 10.4a: Debug Agent Tools (Cloud-side) | branch: | commit:
- [ ] 10.4b: Chat Agent Tools (Cloud-side) | branch: | commit:
- [ ] 10.5: Chat Agent (LangGraph) | branch: | commit:
- [ ] 10.6: Debug Agent (LangGraph) | branch: | commit:

## Phase 11: Frontend — AI Chat & Debug

> Depends on: Phase 9 and Phase 10 complete

- [ ] 11.1: SSE Client & Chat Store | branch: | commit:
- [ ] 11.2: Chat Panel UI | branch: | commit:
- [ ] 11.3: Debug Wizard | branch: | commit:
- [ ] 11.4: Debug Progress & Report | branch: | commit:
- [ ] 11.5: Edge Cases & Connection Switch | branch: | commit:

## Phase 12: Integration & Polish

> Depends on: Phase 11 complete

- [ ] 12.1: Connection Switch Full Reset | branch: | commit:
- [ ] 12.2: End-to-End Flow Tests | branch: | commit:
- [ ] 12.3: Docker Compose Production | branch: | commit:

---

## Dependency Graph

```
Phase 1
  |
  +---> Phase 2 ---> Phase 3 ---+
  |                              |
  +---> Phase 4 ----------------+---> Phase 5 ---> Phase 6 ---> Phase 7 ---> Phase 8
                                                                                |
                                                                    +-----------+-----------+
                                                                    |                       |
                                                                Phase 9                 Phase 10
                                                                    |                       |
                                                                    +-----------+-----------+
                                                                                |
                                                                            Phase 11 ---> Phase 12
```

## Parallelizable Groups

| Group | Phases | Condition |
|-------|--------|-----------|
| A | Phase 2 + Phase 4 | After Phase 1 complete |
| B | Phase 9 + Phase 10 | After Phase 8 complete |
