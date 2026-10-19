# Records and replies

The tracker item holds the detail; the chat thread gets one short reply that
points at it. Both are written only when the user names the write. Use the
team's working language, never mention that an agent or a skill did the work,
and never paste a table or a bullet list into chat.

## Approval record (tracker item)

```markdown
## Deployment approval

**Verdict:** approved
**Checked at:** 2026-02-01T12:40:00+00:00

### Changes

| Change | State | Review | Checks | Mergeable | Verdict |
| --- | --- | --- | --- | --- | --- |
| repository#482 | MERGED | APPROVED | 6 passed | - | approvable |

### Exemptions

- dependency scan: FAILURE exempted as a declared non-blocking check

### Context

- Blocking items: none open
- Request thread: <link>
```

The table is the `--markdown` output of `scripts/pr_gate.py`. Leave the
exemptions section out when none applied; never leave it out when one did.

## Hold record (tracker item)

```markdown
## Deployment approval on hold

**Verdict:** hold
**Checked at:** 2026-02-01T12:40:00+00:00

### Reasons

- PR_NOT_APPROVED (repository#483): review decision REVIEW_REQUIRED, no review submitted
- CI_FAILED (repository#483): unit: FAILURE

### Required actions

1. Obtain an approval on repository#483.
2. Re-run or fix the unit check and confirm the latest run passes.

### Reference

- Changes checked: repository#482, repository#483
- Request thread: <link>
```

Every reason is an observable fact with its code, never an impression. The
status of the item is not changed on a hold.

## Thread replies

Approval, mentioning the requester (the root message's author):

```text
@requester KEY is approved for deployment; the item is now in the ready state
and the details are recorded on it.
```

Hold, mentioning the worker (the mentioned owner or the item's assignee):

```text
@worker the deployment request for KEY is on hold: the pull request still
needs approval and a check is failing. The full reasons and next steps are on
the item.
```

Two to four sentences, one-line reason summary, pointer to the record. If the
item was already in its ready state, say only that, and transition nothing.

## Read back after a transition

1. Fetch the item again.
2. Confirm the status is the ready state that was targeted.
3. Confirm the dates and assignee were not cleared by the transition.
4. Confirm the record comment is present once, not twice.

Report what was written and what was read back. If a write did not take, say
so; do not report completion.
