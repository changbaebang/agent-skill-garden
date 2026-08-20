---
name: hygiene-review
description: >-
  Reviews pull-request hygiene across dependencies, lockfiles, exports, workspace
  boundaries, generated artifacts, duplication, dead additions, and debug residue.
  Use for hygiene review, dependency review, lockfile review, export review,
  monorepo consistency, or cleanup review. Keep correctness blockers in
  critical-review.
---

# Hygiene review

Inspect the changed source and its repository relationships. Read
[references/checklist.md](references/checklist.md) and report only concrete,
actionable drift introduced by the change.

Hygiene findings can include:

- a new dependency without use, missing manifest entry, wrong workspace, or
  incorrect runtime/development classification;
- lockfile state inconsistent with manifest changes, or unexplained broad churn;
- accidental expansion of a package's public export surface;
- new unreachable files, symbols, or duplicate sources of truth;
- debug statements, temporary bypasses, test-only behavior, or generated output
  leaking into production source;
- an evidenced repository-layer or workspace convention violation.

Similar-looking code is not enough to demand abstraction. Show that the new
copies share a change axis and can drift. Do not flag formatting, naming, or a
different but valid local pattern.

Use `must fix` for deterministic configuration, dependency, export, or artifact
inconsistency. Use `should fix` for concrete maintainability drift that does not
block runtime correctness. Omit nits unless the user explicitly requests them.

This pass does not replace critical, framework, language, or side-effect review.
Follow the caller's output contract when selected by `pull-request-review`.
