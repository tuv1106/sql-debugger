---
name: todo-workflow
description: >
  Workflow for selecting, starting, and completing tasks from the project's todos.md file.
  Use this skill whenever the developer asks to "pick a task", "what should I work on next",
  "start the next task", "work on todos", or any reference to task selection and completion.
  Also triggers when the developer says "mark as done", "task is finished", or "what's left to do".
  This skill works hand-in-hand with the git-workflow skill.
---

# Todo Workflow

This skill defines how to select tasks from `todos.md`, work on them, and mark them complete. Task details (Purpose, Context, Files, Tests, Spec references) live in `docs/plans/2026-03-05-implementation-plan.md`.

## todos.md Format

The `todos.md` file is organized in **Phases** with numbered **Tasks**. Each task has:

```markdown
- [ ] 2.3: Entity Exclusion Model | branch: | commit:
```

- `[ ]` / `[x]` — task status
- Task ID and name — matches the implementation plan
- `branch:` — filled when work starts
- `commit:` — filled when task is complete (final commit hash)

Phase headers include dependency notes:
```markdown
## Phase 3: Frontend — Connection Management
> Depends on: Phase 2 complete
```

The bottom of `todos.md` has a **Dependency Graph** and **Parallelizable Groups** table.

## 0. Start-of-Session Sanity Check

**Run this at the start of every new session before doing any work.**

### 0.1 Pull Latest

```
git checkout main
git pull origin main
```

Read `todos.md` to understand current progress.

### 0.2 Find Last Completed Task

Scan `todos.md` for checked tasks `[x]`. Identify the most recently completed task(s) — these are the ones whose work you need to verify before building on top of.

### 0.3 Sanity Check Previous Task

For the last completed task, run these mechanical checks:

**A. Files exist:**
Look up the task in the implementation plan (`docs/plans/2026-03-05-implementation-plan.md`). Every file listed under "Files: Create" must exist on disk.

**B. Test count matches:**
Count the number of test functions in the task's test file(s). Compare to the task's "Tests (N)" count. The actual count should be within reasonable range (not significantly fewer).

**C. Key symbols exist:**
The main classes, functions, and endpoints mentioned in "What to implement" should be findable via grep. For example, if the task says "create `ExclusionConfig` with `is_excluded()`", grep for `class ExclusionConfig` and `def is_excluded`.

**D. Tests pass:**
Run the task's tests and verify they all pass.

### 0.4 If Sanity Check Fails

**STOP.** Do not proceed. Notify the developer with specifics:

```
BLOCKED: Task 2.3 is marked done but:
- Missing file: local_backend/models/entities.py
- Expected ~24 tests, found 18
- Could not find: def sync_new_tables
- 2 tests failing: test_parent_demotion, test_sync_new_tables
```

Wait for the developer to resolve the issue before continuing.

### 0.5 If Sanity Check Passes

Proceed to task selection (Section 1).

## 1. Selecting a Task

### 1.1 Read todos.md

Parse all tasks. For each, identify:
- Task ID and name
- Status: `[ ]` (pending) or `[x]` (done)
- Phase dependency (from the `> Depends on:` note)

### 1.2 Check Dependencies

A task is **unblocked** only when:
- All tasks in earlier required phases are `[x]`
- All tasks within the same phase that come before it are `[x]` (tasks within a phase are sequential)

Exception: Parallelizable Groups (see bottom of `todos.md`) can run concurrently.

### 1.3 Filter to Available Tasks

Keep only tasks where:
1. Status is `[ ]`
2. All dependencies are `[x]`

### 1.4 If No Tasks Are Available

Inform the developer:
- List which tasks remain
- Explain what each is blocked on
- Ask how to proceed

### 1.5 If Multiple Tasks Are Available

This happens at parallelization points (e.g., Phase 2 + Phase 4 after Phase 1). Present the options to the developer and ask which to work on. Reference the Parallelizable Groups table.

### 1.6 If Exactly One Task Is Available

Proceed with that task.

### 1.7 Verify Task Is Not Already In Progress

Before starting, check:
1. Git branches for this task: `git branch -a | grep <task_id>`
2. Recent commits: `git log --oneline -20`

If a branch exists but the checkbox is unchecked, STOP — the task may be in progress from another session. Notify the developer.

### 1.8 Read the Task Details

Read the task entry in `docs/plans/2026-03-05-implementation-plan.md`. Understand:
- **Purpose** — what this task achieves and why
- **Context** — how it fits in the system
- **Files** — what to create or modify
- **What to implement** — the requirements
- **Tests** — expected test count and coverage
- **Spec reference** — which doc section to read for full details

Then read the referenced spec document section.

### 1.9 Create a Branch

Follow `skills/git/SKILL.md` → Section 1 to create the feature branch.

Update `todos.md` with the branch name:
```markdown
- [ ] 2.3: Entity Exclusion Model | branch: `feat/2.3-entity-exclusion-model` | commit:
```

## 2. Working on the Task

Develop the feature following:
- The task description in the implementation plan
- The referenced spec document(s)
- The acceptance criteria and test counts

Follow `skills/git/SKILL.md` → Section 2 for incremental commits.

## 3. Knowing When a Task Is Done

A task is done when:
1. All files listed in the task exist
2. All tests pass
3. Test count roughly matches the expected count
4. Key classes/functions/endpoints from "What to implement" are implemented
5. The acceptance criteria from the implementation plan are met

## 4. After Task Completion

### 4.1 Final Verification

Run all tests for the task one final time. Verify they pass.

### 4.2 Update todos.md

Mark the task checkbox and fill in the commit hash:
```markdown
- [x] 2.3: Entity Exclusion Model | branch: `feat/2.3-entity-exclusion-model` | commit: `abc1234`
```

### 4.3 Commit, Push

Follow `skills/git/SKILL.md` → Sections 3 and 4. The `todos.md` update should be included in the final commit.

### 4.4 Ask Permission

After completing the task, inform the developer:

```
Task 2.3 (Entity Exclusion Model) is complete.
- Branch: feat/2.3-entity-exclusion-model
- Tests: 24/24 passing
- Commit: abc1234

Next available task(s):
- 2.4: Config Store (depends on 2.3 ✓)

Should I continue to Task 2.4?
```

**Wait for the developer's response.** Do not start the next task without permission.
