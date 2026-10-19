---
name: ticket-lifecycle
description: >-
  Creates, splits, estimates, and closes tracker tickets with every required
  field: parent, dates, points, estimate, actual effort. Use for create the
  ticket, split this ticket, over the point cap, estimate MD, close the
  ticket, 티켓 만들어, SP 분할, Done 처리. Not for doing the work or deployment
  tickets; writes need approval.
---

# Ticket lifecycle

A ticket is a record that other people, dashboards, and roll-ups read after you
have moved on. Each lifecycle state has fields that must be present and
well-formed, and the cheapest moment to get them right is the write that moves
the ticket into that state. A leaf is a ticket that carries work and points; a
container only groups leaves. Draft every change first, apply it only when the
user approves, and read the ticket back after each write.

## Resolve the contract before touching the tracker

Field identifiers, the point scale and per-ticket cap, effort granularity, the
leaf issue type, and transition names differ between trackers and teams. Take
them from the environment profile's tracker section or from the user. When a
value is missing, read the tracker's field and type metadata or ask; do not
reuse values remembered from another project, and never guess a custom field
key. Missing configuration is a gap to report, not permission to infer.

The contract this skill enforces is in
[references/field-contract.md](references/field-contract.md): what each state
requires, and why estimate and actual effort follow different rules.

## Pick the leaf issue type once, before the first create

Many trackers have a hierarchy: a parent type, a standard leaf type that takes a
parent link, and a sub-task type. Create leaves as the standard type with the
parent set. A ticket created as a sub-task cannot be converted through the API,
connectors rarely expose delete, and the repair is a manual move per ticket by
the user. When the tracker rejects a type name, look the names up in its
metadata (they match on the untranslated name) instead of trying the next
synonym. Guessing is how six wrong tickets get created in a row.

## Create a leaf

1. Confirm scope and acceptance criteria from the parent's plan or from
   [intake](../intake/SKILL.md); run that first when scope is still open.
2. Size it on the team's point scale. If it exceeds the cap, split first.
3. Confirm parent, start date, due date, and estimated effort. Estimate is a
   judgment recorded at the team's coarse step (commonly half a day); it is not
   derived from points by a divisor, and two tickets with different points may
   carry the same estimate. Ask when it is ambiguous.
4. Create with every required field in one call. Custom fields go where the
   connector expects them; a field silently dropped at create is the most
   common way a ticket lands on the "incomplete" widget.
5. Read the ticket back. Backfill anything missing, within the approved scope.
6. Update the parent's leaf table and summary comment only when the parent is
   yours. A parent owned by someone else gets no write at all, not even a
   comment; put the note on the leaf and follow
   [parent-ticket-guard](../parent-ticket-guard/SKILL.md).

## Split when points exceed the cap

Split by independently mergeable, independently verifiable outcome, not by file
or layer; [work-triage](../work-triage/SKILL.md) produces that slicing. Then:

- the original becomes a container: points cleared, summary marked, description
  holding the leaf table with the total;
- every leaf goes through the create procedure with all fields;
- work, sprints, and point totals live on leaves only, so nothing is counted
  twice;
- if work is already in progress, move the matching leaves to the same state.

## Investigation that ends in implementation

Close the investigation ticket as an investigation: small points, actual effort
as measured, and the findings matrix kept in its description or comments. Open
one implementation leaf per deliverable unit with the full contract, comment
the links back on the investigation ticket, and never leave implementation
points on the investigation ticket when it closes.

## Close

1. Read the ticket and check every done-state field. If actual effort is empty,
   ask the user; a worklog is a hint, not an answer. Zero is a value, empty is
   not.
2. Write actual effort at its fine step (as measured, not rounded to the
   estimate step), then find the done transition by name, because transition
   ids vary per project, and apply it.
3. Read back. Confirm the state and that no required field was cleared.
4. Roll up: when every leaf under a container is done, close the container and
   leave a summary comment on the parent you own; on a foreign parent, the
   roll-up stays on the container.

Do not move a backlog item into progress, or invent dates, to clear a dashboard
warning. A backlog ticket with no dates is correct; an in-progress ticket with
no dates is the violation.

## Check the contract deterministically

Extract the ticket's fields under the logical names in the reference and run:

```bash
python3 scripts/check_ticket_fields.py --state done ticket.json
```

It reports missing fields, off-scale points, over-cap points that require a
split, estimate or actual values off their step, and date problems, and exits
non-zero on any failure. Pass `--scale`, `--cap`, `--estimate-step`, and
`--actual-step` from the profile when the team's values differ from the
defaults.

## Write boundary

Reading, drafting, and writing are separate actions. Show the proposed fields or
transition, apply it only on the user's approval of that specific change, and
report every write with its read-back. A comment is a write too, and a parent
you do not own is outside this skill's write authority.

Templates and the close checklist are in
[references/split-and-close.md](references/split-and-close.md).
