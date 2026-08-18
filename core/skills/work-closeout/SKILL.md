---
name: work-closeout
description: >-
  Closes an engineering work unit by verifying acceptance criteria, diff scope,
  tests, runtime behavior, consumer impact, and residual risk, then preparing a
  reviewable handoff. Use for finish this work, ready for PR, 작업 마무리, 마감,
  or 다음 작업으로. Do not commit, push, merge, publish, or update trackers unless
  the user explicitly requests the specific action.
---

# Work closeout

Completion is an evidence claim, not a feeling.

## Verify

1. Compare the final diff with the stated scope and acceptance criteria.
2. Identify accidental, unrelated, generated, and debug changes.
3. Run proportionate focused checks and record exact outcomes.
4. Trace consumers for shared contracts or runtime state.
5. Exercise changed user-visible behavior when a runnable environment exists.
6. Classify unavailable checks as blocked and state residual risk.

## Prepare the handoff

Summarize what changed, evidence, known limitations, rollback or containment,
and the next requested action. Keep commits, pushes, pull requests, merges,
messages, deployments, and tracker transitions behind explicit authorization.

Use [references/closeout-checklist.md](references/closeout-checklist.md).
