---
name: git-workflow
description: >
  Standard git workflow for feature development: branching, committing, pushing, and opening PRs.
  Use this skill whenever you need to create a branch, make commits, push code, or open a pull request.
  Also use when the developer asks to "commit", "push", "open a PR", "create a branch", or any
  git-related development workflow step. This skill should be triggered even for partial steps
  like "push my changes" or "commit what I have".
---

# Git Workflow

This skill defines the standard git workflow for feature development. Follow these steps in order.

## 1. Create a New Branch

1. Checkout the `main` branch:
   ```
   git checkout main
   ```
2. Fetch and pull latest changes:
   ```
   git fetch origin
   git pull origin main
   ```
3. Create a new branch with the naming convention `feat/<task_id>-<short-name>`:
   ```
   git checkout -b feat/<task_id>-<short-name>
   ```
   The task ID and name come from `todos.md`. Use hyphens to separate words. Keep the name concise.

   **Examples:**
   - `feat/2.1-connection-models`
   - `feat/4.1-sql-parser-service`
   - `feat/10.4a-debug-agent-tools`

## 2. During Development

- **Commit incrementally.** Do not wait until the entire feature is done to make one giant commit. Break work into logical, meaningful commits as you go.
- **Stash or commit WIP** before switching branches. Never leave uncommitted changes when moving to another branch.

## 3. Commit

Before every commit, run through this checklist **in order**. Do not skip steps.

### 3.1 Run All Tests

Run the project's test suite for the task. All tests must pass before committing.

- **If a test fails and it is related to your changes:** fix the code until the test passes.
- **If a test fails and it is NOT related to your changes:** STOP. Present the failing test to the developer and wait for instructions.

### 3.2 Check Code Styling

Review the code against the project's `CLAUDE.md` style guidelines. If the code does not match, fix it before committing.

### 3.3 Verify Feature Matches Requirements

Before committing, verify that the feature matches:
- The **task definition** in the implementation plan (`docs/plans/2026-03-05-implementation-plan.md`)
- The **spec documents** referenced in the task

If something doesn't match, stop and flag it to the developer.

### 3.4 Write the Commit Message

Write a clear, detailed commit message that explains **what was done**. Include specifics.

**Good examples:**
```
feat: add ExclusionConfig with is_excluded and parent demotion logic

- PostgresExclusionConfig, MySQLExclusionConfig, BigQueryExclusionConfig
- O(1) lookup via denormalized blocked_schemas + blocked_tables
- No auto-promotion rule enforced
- 24 tests covering all exclusion/inclusion scenarios

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

```
fix: handle missing keyring entry gracefully in ConfigStore

- reconcile() now marks connections as needs_reauth instead of crashing
- Added 3 tests for missing password scenarios

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```

**Bad examples:**
```
fixed stuff
```
```
updates
```

### 3.5 Rebase on Main

Before pushing, rebase your branch on the latest `main`:

```
git fetch origin
git rebase origin/main
```

- **If there are merge conflicts:** STOP. Do NOT attempt to resolve them. Inform the developer and wait for instructions.
- **Never force push.** Under no circumstances use `git push --force` or `git push -f`.

### 3.6 Push

Push your branch to the remote:

```
git push origin feat/<task_id>-<short-name>
```

### 3.7 Code Quality Checklist

Before committing, verify:
- All functions have type hints
- Complex logic has docstrings
- No hardcoded credentials or secrets
- Error messages are helpful
- No unused imports or variables
- No print() statements (use logging)

## 4. Open a Pull Request

Once the branch is pushed, open a Pull Request targeting `main`.

Use `gh pr create` with a clear title and body:
```
gh pr create --title "feat: <short description>" --body "$(cat <<'EOF'
## Summary
<1-3 bullet points>

## Task
Task <id>: <name> from implementation plan

## Test plan
- [ ] All task tests pass
- [ ] Sanity check: files exist, key symbols defined

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

## 5. NEVER Change the Git Remote URL

The remote is configured as HTTPS (`https://github.com/...`). **Do NOT change it to SSH** (`git@github.com:...`). The developer's credentials are configured for HTTPS — switching to SSH will break push/pull.

## 6. Files That Must NEVER Be Committed

The following must never be committed:

- `.env` files (environment variables, secrets)
- `.idea/` directory (IDE settings)
- `.claude/` directory (AI assistant configuration)
- `.venv/` directory (virtual environment)
- Any secrets, API keys, tokens, passwords, or sensitive data
- Any credentials or authentication material

If you notice these files are staged, remove them from staging and verify they are in `.gitignore`.
