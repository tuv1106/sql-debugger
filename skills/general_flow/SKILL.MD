---
name: general-workflow
description: >
  Plan-first development workflow: read context, plan, get approval, implement, and retrospect.
  Use this skill whenever starting any coding task, feature, bug fix, or refactor. This is the
  overarching workflow that wraps around todo-workflow and git-workflow. Triggers on: "start working",
  "implement this", "build this feature", "fix this bug", any task from todos.md, or whenever
  Claude is about to write code for a non-trivial change. If the task involves more than a
  one-line fix, use this workflow.
---

# General Workflow

This skill defines the plan-first development workflow. Every non-trivial coding task follows these steps in order. This workflow wraps around `todo-workflow` and `git-workflow`.

## 0. Session Start

At the start of every session, follow `skills/todo_workflow/SKILL.md` → Section 0 (Start-of-Session Sanity Check). This verifies that previous work is solid before building on top of it.

## 1. Read Context

Before doing anything else, read and internalize the project constraints and task requirements.

### 1.1 Read CLAUDE.md

Read the project's `CLAUDE.md` file. Understand the code style rules, conventions, architectural decisions, and constraints.

### 1.2 Read the Task Requirements

Read the relevant sources for this task:
- The task entry in `docs/plans/2026-03-05-implementation-plan.md` (Purpose, Context, Files, Tests, Spec reference)
- The referenced spec document section
- The task status in `todos.md`

### 1.3 Read the Existing Code

Before planning any changes, read the files you expect to modify or that are related to the task. Understand:
- The patterns already in use (naming, structure, error handling)
- How existing modules interact
- What tests already exist for related code

Do not skim. Actually read the code.

## 2. Scope Check

Before planning, assess whether the task is well-defined and reasonably scoped.

**Flag to the developer and wait for guidance if:**
- The requirements are unclear or contradictory
- The spec doc is missing details needed to implement
- The task seems significantly larger than its description suggests
- There are unresolved questions that would change the approach

Do not proceed with open questions. Resolve them first.

## 3. Implement

Execute the task. Write code and tests as described in the implementation plan.

### 3.0 Environment & Dependencies

Before writing any code, ensure the virtual environment is active and dependencies are installed:
- If `.venv` does not exist, create it: `python3 -m venv .venv`
- Activate it: `source .venv/bin/activate`
- If the task requires new dependencies, add them to `requirements.txt` and run `pip install -r requirements.txt`
- Always work inside the venv — never use the system Python.

For frontend tasks:
- `cd frontend && npm install` if needed
- Use `npm run test` for vitest

### 3.1 Follow TDD

For each piece of functionality:
1. Write the test first
2. Run it — verify it fails
3. Implement the code
4. Run it — verify it passes
5. Move to the next piece

### 3.2 Follow the Implementation Plan

The task in `docs/plans/2026-03-05-implementation-plan.md` already has:
- Files to create/modify
- What to implement
- Expected test count
- Spec reference for details

Use this as your guide. Adapt if reality doesn't match, but stay within scope.

### 3.3 Incremental Progress

Follow `skills/git/SKILL.md` → Section 2 (During Development) for committing incrementally.

### 3.4 When Unexpected Issues Arise

If something comes up that you didn't anticipate — a needed refactor, an edge case, a dependency you missed — handle it as long as:
- The overall goal of the task is still achieved
- The change stays within scope
- The change follows `CLAUDE.md` conventions

If the unexpected change is significant (new files, different approach, expanded scope), stop and check with the developer.

## 4. Complete the Task

After implementation is complete:

1. Follow `skills/todo_workflow/SKILL.md` → Section 4 (After Task Completion) to mark checkboxes, commit, push, and update `todos.md`.
2. Follow `skills/git/SKILL.md` → Sections 3 and 4 (Commit and Push/PR).
3. Ask the developer for permission before starting the next task.

## Workflow Summary


```
Session start (sanity check previous work)
    |
Read context (CLAUDE.md -> implementation plan -> spec docs -> existing code)
    |
Scope check (flag issues -> wait if unclear)
    |
Implement (TDD: test first -> implement -> verify)
    |
Complete (update todos.md, commit, push, ask permission)
```
