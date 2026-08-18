---
name: collaboration-awareness
description: >-
  Compares current changes with active branches or open pull requests to detect
  file, module, dependency, and cross-workstream conflicts before implementation
  or merge. Use for overlapping work, concurrent changes, conflict check,
  겹치는 작업, 다른 PR과 충돌, or 누가 같은 파일 건드리나. Read-only; do not
  comment, merge, rebase, or contact authors automatically.
---

# Collaboration awareness

1. Collect committed and uncommitted changed files for the current work.
2. Resolve its branch, pull request, and workstream metadata when available.
3. List active work from the repository's available source of truth.
4. Exclude the current branch or pull request from comparisons.
5. Compare exact files, module boundaries, dependency relationships, and workstream ownership.

Prioritize observable overlap. Do not claim a conflict from a shared top-level
directory alone. When dependency data is unavailable, label that level blocked.

Report the competing work, evidence, likely failure or coordination cost, and a
recommended human coordination step. Never post comments or change branches as
part of this skill.

Use [references/conflict-levels.md](references/conflict-levels.md).
