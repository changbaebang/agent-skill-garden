---
name: pull-request-checklist
description: >-
  Checks a pull request's description against its template and merge gates:
  hard and soft gates, tier rationale, tracker link, evidence, base-branch
  strictness. Use for PR checklist, PR quality gate, fill the PR body, PR 템플릿
  점검, PR 본문 채워줘. Not for diff review or reviewer replies; read-only
  unless asked to update it.
---

# Pull request checklist

A change can pass code review and still be unmergeable: the description is a
template skeleton, the risk tier is missing or unexplained, the ticket is not
linked, or "QA passed" has no evidence behind it. This workflow judges the
request's metadata and template, not the code. Route code findings to
`pull-request-review`; route reviewer replies to `review-response-loop`.

## Establish the request

1. Fetch the title, description, base, head, changed files, commits, and diff
   summary. Judge the current head, not a remembered one.
2. Read the repository's own pull-request template and contributing notes to
   learn which sections exist and which are required. The template is the
   authority; do not assume section names from memory or from another project.
3. Classify the base branch: **production-bound** (default branch, release,
   production, hotfix) or **integration** (develop, staging, QA, a feature
   integration branch). `scripts/pr_body_sections.py classify-base` applies
   the default patterns; override them when the repository names its branches
   differently.
4. Extract the tracker key from the title with
   `scripts/pr_body_sections.py ticket-key`. Keep the full key; a truncated key
   links to the wrong ticket or to nothing. Build the link from the tracker
   base URL in the environment profile or from the template's own example.
   When neither defines it, keep the plain key and say the link is unknown.

## Evaluate the gates

Read [references/gates-and-decision.md](references/gates-and-decision.md).

**Hard gates** decide approval: requirement implemented, no obvious correctness
bug in a changed critical flow, failure preparedness where the change needs it
(flag, fallback, rollback), verification evidence present, no debug leftovers,
no high-impact typo. **Soft gates** shape the comment: clarity, convention,
documentation, impact analysis, tier rationale.

Evidence must be visible in the description, the diff, or a linked test, run,
or document. Do not invent it. A claim of passing QA with no link is a missing
gate, not a passed one. Record "not verifiable from here" as a limitation and
let it count against the gate, never for it.

## Risk tier

When the repository defines a tier scale, use its labels verbatim, including
any emergency or hotfix class that sits outside the numbered levels. Never emit
a bare number when the scale has names, and never invert the scale: the highest
severity is the highest tier. A tier without a one- or two-sentence rationale
fails the soft gate even when the value is right.

Propose a default only as a proposal: authentication, payment, permissions, or a
core transaction suggests the highest tier; navigation, conversion flow, or API
behavior suggests the middle; copy or style alone suggests the lowest. When the
repository has no tier field, report that instead of inventing one.

## Typos by impact

Judge a misspelling by what it breaks, not by its presence. A wrong symbol,
import, environment key, API field, or path that changes build or runtime
behavior is a hard-gate failure. A misspelling in a comment, document, or
non-critical copy is a soft-gate remark. Report the exact wrong token, the
expected token, and the concrete impact.

## Decide by branch

| Situation | Decision |
| --- | --- |
| Production-bound and any hard gate fails, or a clear severe risk anywhere | request changes |
| Only soft-gate issues | comment |
| Integration branch with WIP or temporary mock, mitigated and low immediate risk | comment, with the downgrade record below |
| Hard gates pass with reasonable confidence and no open concern | approve |

A downgrade on an integration branch is only valid when the required actions
name the follow-up ticket, the owner, and the target branch or date before the
change reaches production. The same issue on a production-bound request is a
request for changes.

## Update the description only when asked

A checklist request does not authorize editing the description. When the user
asks to fill or fix it, read [references/body-update.md](references/body-update.md)
and:

- touch only the metadata sections the template defines for this purpose;
  leave checklists, comments, and every other section byte-stable;
- write factual bullets from the diff and commits, not restatements of the
  title;
- make the edit idempotent at section level with
  `scripts/pr_body_sections.py upsert`, which replaces content under a heading,
  inserts missing sections in the template's order, keeps template comments
  and anything after a horizontal rule, and drops exact duplicate bullets;
- show the resulting diff of the description before applying, apply once with
  `scripts/pr_body_patch.sh`, then read the description back.

## Output

```markdown
## Decision
- approve | comment | request changes

## Checklist result
- [hard] item: pass | fail - evidence or the missing evidence
- [soft] item: pass | needs improvement - reason

## Required actions
- concrete action (downgrade: follow-up ticket, owner, target)

## Comment draft
- a short comment ready to post, in the repository's working language
```

## Write boundary

Posting the review or comment, adding labels, and patching the description are
external mutations. Present the draft first and perform a write only for the
action the user named. Never approve on this checklist alone when the user also
expects the code to be reviewed; say which review is still missing.
