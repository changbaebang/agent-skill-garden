---
name: work-start
description: >-
  Starts a defined engineering work unit by checking scope, base revision,
  worktree state, concurrent work, verification commands, and mutation authority.
  Use for start this work, create the work branch, 작업 시작, 브랜치 만들어, or
  다음 작업 시작. Read-only preflight is automatic; create branches or update
  trackers only when the user's request authorizes those actions.
---

# Work start

Run a preflight before editing.

1. Restate the goal and acceptance criteria.
2. Resolve the repository, intended base, and current revision.
3. Inspect committed and uncommitted changes separately.
4. Preserve unrelated and pre-existing changes.
5. Identify likely consumers, test commands, and runtime verification.
6. Check concurrent work when repository metadata is available.
7. State which next actions are read-only and which mutate local or external state.

Do not assume the default branch is the correct base. Do not stash, reset, clean,
or switch away from user work to manufacture a clean baseline.

If authorized to create a branch, use the repository's naming rules and verify
the resulting branch and base. If not authorized, report the proposed command or
branch name without executing it.

Use [references/start-checklist.md](references/start-checklist.md) as the handoff.
