---
name: deployment-approval-ticket
description: >-
  Creates a deployment approval ticket from the live approval guide, never by
  copying an old ticket. Use for deploy ticket, deployment approval ticket,
  배포 티켓, 배포 승인 티켓, or fix the approval bot's missing-field comment. Not
  for QA sign-off docs, go/no-go calls, or plain work tickets. Drafts only;
  never requests approval.
---

# Deployment approval ticket

The guide that defines a valid approval ticket changes without an announcement,
and an automated gate enforces the current version the moment the ticket enters
the approval step, often on the morning the change ships. A ticket cloned from
last month's example carries last month's rules. One such rule flipped from
"omit the second-approver section below the top risk tier" to "write both
sections at every tier"; every ticket built from the older shape was rejected at
the gate. Re-reading the guide is the only defense.

## Read-write boundary

"Make the deployment ticket" authorizes creating one draft ticket and the link
to its work item, nothing more. Moving it into the approval queue, posting about
it in chat, commenting, or editing other tickets each need their own request.
Closing the ticket after the deployment is a later, separate change; it follows
[ticket-lifecycle](../ticket-lifecycle/SKILL.md).

## 1. Re-read the guide, every time

Resolve where the guide lives from the environment profile or ask for it. Do not
proceed from memory, from this file, or from an earlier ticket. Extract:

- the structured fields the gate reads: risk tier, first and second approver,
  start and due dates, summary convention;
- the body headings it requires, as exact text, and the items under each;
- which tiers need which approvers, and whether lower tiers omit a section or
  mark it not applicable;
- how the work item must be linked.

An earlier ticket is precedent for content: what a good rollback trigger or a
clear risk statement looked like. It is never a template for structure. See
[references/guide-extraction.md](references/guide-extraction.md).

## 2. Collect inputs; refuse to guess

Required: the change reference (pull request or equivalent), deployment date,
risk tier, approvers, assignee. Stop and ask for whatever is missing rather than
create a ticket that fails validation.

- Dates come from the user. Normalize month/day input in the profile's time
  zone; never infer from merge time, tracker dates, or today.
- Propose the guide's default tier when none is given, but never lower a
  high-risk change on your own.
- Approvers come from the guide's roster or the user. When the top tier gets the
  same person in both approver roles, ask once; independent second review is
  the point, but teams differ.

## 3. Check for an existing ticket

Search the approval project for the change reference and the primary work item.
If a ticket exists, report it and stop.

## 4. Gather evidence

From the change: title, body, state, head revision, changed paths, linked work
items, verification results, reviewers, and any precedent where the same change
already shipped elsewhere. Precedent is the strongest evidence an approver can
get; link it.

## 5. Fields are not the body

The gate validates fields and literal headings; approvers read the body. Both
must be right.

- Set tier, approvers, and dates as fields. Start and due date carry the same
  deployment date. Resolve field identifiers from the tracker's create-screen
  metadata; a value visible on an old ticket may belong to a field the create
  screen does not offer, and a similarly named field may be something else.
- Headings match the guide character for character. A list item starts on the
  first line after each heading; a sentence between them reads as missing.
- Write every required section at every tier when the guide says so, with
  "not applicable" instead of omission.
- Checklist items stay unchecked at creation.

Run `scripts/check_ticket_body.py` with the headings copied from the guide
before creating.

## 6. Write for the approver

Each item is an answer, not a question. The rollback trigger names a signal
specific to this change, not a generic latency clause. Residual risk separates
"checked and fine" from "no way to reproduce". Unverified items say what stood
in for verification.

## 7. Create, read back, report

Create the ticket in draft state. Link the primary work item in the relation the
guide prescribes, skipping links that already exist. Then read the ticket back:
the create response omits several fields. Compare assignee, approvers, tier,
both dates, links, and each heading with its first list item. Fix and read
again. Report the ticket, tier, approvers, dates, and linked work. If a required
value did not save, say so; do not report completion.

The ticket is a record that deployment dashboards and audits read later. Never
change its status or dates to clear a dashboard warning or hide it from a list.

## Repairing a gate finding

When the user pastes a missing-field comment, re-read the guide first. The gate
may cite guide section numbers that are not field names; map each item to a
field or a heading as described in
[references/create-and-verify.md](references/create-and-verify.md), fix only
those, and read back.
