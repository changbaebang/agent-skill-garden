# Verification

Verification must match the risk of the change.

- Trace the real runtime path and consumers for shared changes.
- Prefer focused checks that exercise the changed behavior.
- Distinguish `pass`, `fail`, and `blocked`.
- Never convert an unavailable check into a pass.
- Record residual risk when a relevant environment or integration cannot be tested.
- Preserve dirty worktrees; do not use destructive baseline tricks.
