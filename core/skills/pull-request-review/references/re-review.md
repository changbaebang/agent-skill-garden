# Re-review and fix verification

## Establish the delta

- Record the previously reviewed head and current head.
- Read unresolved threads and author replies before scanning for new issues.
- If the head is unchanged and no new reply or external evidence exists, do not
  review again.
- New findings must come from code changed after the previous review. Do not use
  re-review to discover unrelated problems in unchanged code.

## Reclassify existing threads

Classify each unresolved thread from current evidence:

| State | Requirement |
| --- | --- |
| fixed | Current code demonstrably removes the failure |
| gone | The affected code or path no longer exists in the change |
| accepted reason | Current code is unchanged, but verified evidence makes the behavior valid |
| unresolved | The failure remains, the evidence is insufficient, or verification is unavailable |

Read the current file before marking a thread fixed. A reply saying "fixed" and
a green CI run are leads, not proof. Run a focused runtime or contract check when
static types cannot verify the relevant behavior.

A future issue, follow-up pull request, or planned cleanup does not resolve a
current release blocker. It can resolve a non-blocking maintenance suggestion
only when the current release decision does not depend on it.

## Avoid review whack-a-mole

- Raise all evidenced findings from the current delta together.
- Do not restate the same concern on another unchanged line.
- Do not reopen a disproven finding under a new rationale without new evidence.
- If an author response disproves the original premise, withdraw or reclassify
  it explicitly.
- Do not approve while an unresolved blocker or safety-relevant question remains.

When publication is authorized, verify the current head immediately before the
write, submit one review, and read it back. If the head changed during review,
stop and recompute instead of attaching stale findings.
