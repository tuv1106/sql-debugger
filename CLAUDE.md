# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

This project is in the **design/planning phase**. The `docs/` directory contains detailed specifications and `docs/plans/2026-03-05-implementation-plan.md` has the 53-task implementation plan. Implementation has not begun — there is no source code, no build system, and no tests yet.

## Project Overview

An AI-powered SQL debugging tool with a hybrid local+cloud architecture:

- **Local backend** (Python/FastAPI, runs on user's machine): holds DB credentials, executes queries, enforces table access rules, caps result sizes
- **Cloud backend** (Python/FastAPI + LangGraph, hosted on Railway/Render): runs LLM/agent reasoning — never sees credentials or query results
- **Frontend** (React 19 + TypeScript + Vite): loaded from cloud, runs in browser, talks to both backends independently

**Key security invariant:** credentials and query results never leave the local machine. The cloud only receives query text for AI reasoning.

## Architecture

```
Browser (React frontend)
  ├── localhost:8765  (Local Backend — credentials, query execution)
  └── api.yourapp.com (Cloud Backend — LLM/agent analysis via LangGraph)
        |
      User's DB (Postgres, MySQL, BigQuery)
```

## Tech Stack

| Layer | Choice |
|-------|--------|
| Local + Cloud backends | Python 3.14, FastAPI |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Zustand, CodeMirror 6, React Flow + ELK, TanStack Table |
| SQL parsing | sqlglot (dialect-agnostic) |
| Credentials | OS keyring + encrypted file fallback |
| Agent framework | LangGraph with ChatAnthropic |
| DB libraries | psycopg2, mysql-connector, google-cloud-bigquery |
| Deployment | Docker + docker-compose |

## Development Commands (once implementation begins)

```bash
# Local backend
cd local_backend && uvicorn main:app --port 8765 --reload
pytest tests/local_backend/                    # all local backend tests
pytest tests/local_backend/test_parser_service.py::test_name  # single test

# Cloud backend
cd cloud_backend && uvicorn main:app --reload
pytest tests/cloud_backend/

# Frontend
cd frontend && npm run dev                     # dev server
cd frontend && npm run test                    # vitest

# Full stack
docker compose up                              # all 3 services + test DBs
```

## Spec Documents

| Doc | What it covers |
|-----|---------------|
| `docs/project-overview.md` | Product vision, architecture, MVP scope, security model |
| `docs/01-connection-management-frontend-v2.md` | 6 UI components, 14 endpoints, 36 tests |
| `docs/02-connection-management-backend-v2.md` | Models, storage, exclusions, 132 tests |
| `docs/03-schema-browser-frontend.md` | Tree view, cache strategy, 45 tests |
| `docs/04-query-console-design.md` | Query console high-level design |
| `docs/05-query-console-lineage-detailed.md` | Lineage, execution, results: 5 endpoints, 132 tests |
| `docs/06-ai-chat-and-debugging.md` | AI chat + debug agents, 93 tests |
| `docs/07-cloud-backend.md` | Sessions, SSE, LangGraph agents, 33 tests |
| `docs/plans/2026-03-05-implementation-plan.md` | 53 tasks across 12 phases, ~444 tests |
| `docs/plans/2026-03-05-doc-review-and-decisions.md` | Design decisions and inconsistencies fixed |

## Implementation Plan Structure

12 phases with dependency graph. Key parallelization points:
- Phases 2 (local backend connections) and 4 (schema/query endpoints) can run in parallel after Phase 1
- Phases 9 (AI support endpoints) and 10 (cloud backend) can run in parallel after Phase 8
- Each task references specific spec document sections and lists exact test counts

## Key Design Decisions

- **Snowflake** deferred to post-MVP — focus on Postgres, MySQL, BigQuery
- **Node IDs** have no type prefix: CTE → name, table → qualified name, subquery → parent_alias
- **Injection method** is AST manipulation via sqlglot (not subquery wrapping)
- **Schema browser** hidden by default, toggleable
- **Connection switch** triggers full reset: cancel all in-flight ops, clear all stores
- **Agent scope** limited to within a single query — no cross-query or pipeline debugging

## Git Workflow

- Always check current branch with `git branch` before starting work
- Always branch from `main`, never from another feature branch
- Create a feature branch before making any commits — never commit directly to main
- Branch naming: `feat/<task_id>-<short-name>` (e.g., `feat/2.1-connection-models`)
- Run full test suite before committing
- **NEVER change the git remote URL** — it uses HTTPS and must stay that way
- See `skills/git/SKILL.md` for full workflow

## Planning Before Implementation

- Before writing ANY code, read the implementation plan and relevant spec documents
- Create a plan file and get user approval before implementation begins
- Follow TDD: write tests first, then implement, then verify all tests pass
- Never jump straight to coding without an approved plan
