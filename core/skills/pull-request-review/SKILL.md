---
name: pull-request-review
description: >-
  Routes a pull request through the smallest sufficient set of evidence-based
  review passes, then combines findings and verifies fixes on re-review. Use for
  PR review, code review, review this change, re-review, 수정 확인, 다시 리뷰,
  or merge-readiness review. Read-only unless review publication is explicitly
  requested.
---

# Pull request review

Review the current change, not a remembered snapshot. Establish the repository,
base, head, state, changed files, existing review threads, and repository
instructions before judging the code.

## Route before reviewing

Read [references/routing.md](references/routing.md), inspect the file list and
diff signals, and select the smallest sufficient review set. Always include
`critical-review`. Add framework, language, hygiene, or `side-effect-check`
passes only when their signals are present. The review pack is intended to be
installed together. If a required pass is unavailable, report the coverage gap
instead of silently replacing it with a shallow imitation.

State the selected and skipped passes with one-line reasons. Selection is a
coverage decision, not a finding.

## Review with evidence

For each selected pass:

1. Read each relevant changed file in enough surrounding context to understand
   the change. Skip generated output and binary assets unless a specialized pass
   needs their relationship to source files.
2. Trace callers, consumers, types, effects, configuration, and tests needed to
   prove or disprove a candidate issue.
3. Report only issues introduced by the change. Anchor comments to changed lines,
   but use unchanged code as evidence when necessary.
4. Apply [references/evidence-and-severity.md](references/evidence-and-severity.md).
   Do not turn missing context, preference, or a possible improvement into a
   defect.
5. Run focused checks when they can materially change the verdict. Record
   unavailable runtime evidence as a limitation, not a pass.

## Re-review

When prior review state exists, read
[references/re-review.md](references/re-review.md) before producing new findings.
Verify claimed fixes in the current files and compare the prior reviewed head to
the current head. Do not create a sequence of new findings from code that did not
change.

## Decision and output

Return:

```markdown
## Review scope
- Base/head/state: ...
- Selected passes: ...
- Skipped passes: ...

## Findings
- [blocker | warning | question] `path:line` - trigger, impact, evidence, fix

## Decision
- request changes | comment | approve | no review

## Verification
- Checks run: ...
- Residual or unavailable evidence: ...
```

Use `request changes` only for a current blocker. Use `comment` when a meaningful
warning or safety-relevant question remains. Approve when all prior blocking
threads are resolved and there are no new blocker, warning, or safety-relevant
question findings. Use `no review` for an unchanged reviewed head with no new
author response or external evidence. A closed change can receive explicitly
requested retrospective analysis, but never a new published approval or change
request.

Review publication, thread resolution, labels, approvals, and messages are
external mutations. Perform them only when explicitly requested, publish once,
then read back the resulting review and current head.
