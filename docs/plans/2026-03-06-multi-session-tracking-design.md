# Multi-Session Task Tracking — Design

**Date:** 2026-03-06
**Status:** Approved

## Problem

The implementation plan has 59 tasks across 12 phases. Work happens across multiple Claude Code sessions (sometimes parallel). There's no mechanism for an agent in one session to signal completion, or for the next session to verify previous work before building on it.

## Solution

### Tracking File: `/todos.md`

Lean markdown checklist at repo root. Each task is a one-liner with status, branch, and commit hash. Detailed task specs live in the implementation plan — `todos.md` is just the status dashboard.

Format:
```markdown
- [x] 2.3: Entity Exclusion Model | branch: `feat/2.3-entity-exclusion-model` | commit: `abc1234`
- [ ] 2.4: Config Store | branch: | commit:
```

### Branching: One Branch Per Task

Branch naming: `feat/<task_id>-<short-name>` (e.g., `feat/2.3-entity-exclusion-model`). Each task gets its own branch off `main`.

### End-of-Session Protocol

1. Run all tests for the task — verify pass
2. Commit to task branch
3. Push branch
4. Update `todos.md`: check box, fill branch + commit hash
5. Commit and push `todos.md` update
6. Ask developer permission before continuing to next task

### Start-of-Session Protocol (Sliding Window Verification)

1. Pull latest `main`, read `todos.md`
2. Find last completed task(s), check dependency graph, determine next task
3. Sanity check previous task:
   - **Files exist:** every file in the task's "Files: Create" list exists
   - **Test count matches:** number of test functions roughly matches expected count
   - **Key symbols exist:** main classes/functions/endpoints from "What to implement" are grep-able
   - **Tests pass:** run the task's tests
4. If any check fails → stop, notify developer with specifics
5. If all pass → start implementing next task

### Parallel Sessions

At parallelization points (Phase 2+4 after Phase 1, Phase 9+10 after Phase 8):
- Each session works on a different phase
- Each has its own branch
- Both update `todos.md` — different task lines, minimal conflict risk
- If conflict occurs, agent resolves it (additive-only changes)

## Skill Updates

Three project skills were updated to implement this design:

| Skill | Key Changes |
|-------|-------------|
| `skills/git/SKILL.md` | GitHub + `main` branch, `feat/` prefix, co-author line, no force push |
| `skills/todo_workflow/SKILL.md` | Lean `todos.md` format, start-of-session sanity check, branch/commit tracking, ask permission after each task |
| `skills/general_flow/SKILL.MD` | Skip per-task plan files (implementation plan has detail), add session protocols, TDD approach |

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tracking format | Markdown checklist | Human-readable, agents parse it fine, works as progress dashboard |
| Task detail location | Implementation plan (not todos.md) | Avoids duplication, single source of truth for specs |
| Branching | One branch per task | Clean isolation, easy to review, matches task granularity |
| Sanity check depth | Mechanical (files + tests + grep) | Fast, objective, no subjective code review |
| After-task behavior | Ask permission | Developer stays in control of session flow |
| Per-task plan files | Skipped | Implementation plan already has Purpose, Context, Files, Tests per task |
