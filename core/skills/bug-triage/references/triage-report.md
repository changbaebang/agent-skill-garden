# Triage report templates

Every artifact below is a draft until the user authorizes the write that
publishes it. Posting a tracker comment or a chat message is a separate
decision from producing its text.

## Reproduction table

One row per profile or state actually exercised. "Reproduced" is a value
comparison, not an impression from a screenshot.

| Profile or state | Measured value | Expected value | Reproduced |
| --- | --- | --- | --- |
|  |  |  |  |

When one row is clean and the others are not, add a column for the raw inputs
that row received (user agent, attributes, injected variables, inline
overrides) so a masked profile can be told apart from a fixed one.

## Cause comment

Post as one comment. Do not edit the report description; the reporter's text
is evidence and must stay as filed.

```markdown
## Cause

- One line:
- Evidence (file:line on the base ref):
- Why the values diverge:

## Reproduction

(table above)

## Impact

- Files a fix would touch:
- Consumers of those files:
- Applications or surfaces affected:

## Open questions

- (STOP-C questions, each naming who can answer it)
```

## History comment

Post separately from the cause so a reader can follow the cause without the
archaeology.

```markdown
## History

| When | Change | Intent as stated | Effect on this defect |
| --- | --- | --- | --- |
|  | introducing change |  |  |
|  | later change |  | masked, widened, or added the tool a fix needs |

Timeline check: the report is dated ____; every change listed above landed
before that date.
```

## Stop notice

A stop is not a notification. It names what is awaited, who can clear it, and
where the flow resumes.

```markdown
Stopped at: STOP-A | STOP-B | STOP-C
Awaiting:
Who unblocks it:
Resume at: step __ when the above arrives
Work that continues meanwhile: (STOP-C only: history, test cases)
```

## Test-case split

| Id | Kind | Entry state | Action | Expected result | Where it can run |
| --- | --- | --- | --- | --- | --- |
| N-1 | new behavior |  |  |  | browser or device |
| R-1 | regression |  |  |  | browser or device |

- New (`N-`): behavior that is wrong today and must be right after the fix.
- Regression (`R-`): behavior that is right today and must stay right. Seed
  this list from the consumers found in the blast radius.
- "Where it can run" is browser when a profile matrix reproduces it and
  device only when a real client is required.

## Approval report

Send once, with steps 3 to 5 complete, and end with the question.

```markdown
## Triage summary

- Cause:  (one line, file:line)
- Gate: this team alone | STOP-C waiting on ____ | STOP-B hand off to ____
- Blast radius: __ consumers; regression targets: ____
- Test cases: __ new, __ regression, __ device-only
- Unconfirmed:

Proceed to implementation?
```
