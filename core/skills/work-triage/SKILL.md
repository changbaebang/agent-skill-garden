---
name: work-triage
description: >-
  Classifies scoped engineering work and splits it into independently reviewable,
  mergeable, and verifiable slices. Use for split this work, plan the PRs,
  break down an epic, 작업 나누기, 범위가 큰가, 하위 작업, PR 단위, or 어떻게
  나눌까. Produce a read-only proposal first and do not create issues, branches,
  or pull requests without explicit authorization.
---

# Work triage

Read the intake or available evidence, then choose the smallest sequence that
delivers verifiable progress without hiding dependencies.

## Classify

Use a practical class rather than a project-specific taxonomy:

- behavior change;
- defect or regression;
- migration or replacement;
- mechanical move or rename;
- research or contract discovery;
- operational or release work.

## Slice

Each slice should have one observable outcome, an explicit dependency, and a
verification method. Prefer vertical slices. Separate preparatory refactors only
when they are independently safe and useful.

Do not split solely by file count or implementation layer. Avoid slices that can
only be verified after several later slices land.

## Report

For every proposed slice provide scope, dependency, acceptance criteria,
verification, rollback or containment, and recommended order. Call out work that
should remain in one change because splitting would create an invalid state.

Use [references/slicing-patterns.md](references/slicing-patterns.md) for common
patterns and traps.
