# Inputs, creation, read-back, and repair

## Input contract

| Input | Rule |
| --- | --- |
| change reference | Pull request URL or equivalent. A bare number is accepted only when the repository is unambiguous; normalize to the canonical URL. |
| deployment date | User-provided. Accept `2026-03-04`, `3/4`, or `March 4 16:00`. Keep a date-only value for tracker date fields and a separate date-time value for the body only when the user supplied a time. Resolve month/day input in the profile's time zone against the current date. Never derive it from merge time, tracker dates, or today. |
| risk tier | User-provided or the guide's default. Never lower a tier for a change the guide classifies as high risk. |
| first approver, second approver | From the guide's roster or the user. Never invent one. If the top tier gets the same person twice, ask once. |
| assignee | The requesting user unless they name someone else. |

When any required input is missing, ask for that value only. Do not create a
ticket that will fail validation and promise to fix it later.

If the change is closed without merging, ask before creating.

## Duplicate search

Search the approval project, newest first, for tickets whose text contains the
change number or the primary work item key, or whose summary resembles the
intended summary. If one exists, report it and stop. Creating a second ticket
splits the approval trail.

## Evidence to collect from the change

- title, body, state, merged or not, head revision
- changed paths, which also decide the affected domains the guide asks for
- linked work items: the key in the title or the labeled primary entry is the
  primary work item; keep secondary references in the body without linking them
- check and review state, reported as evidence, not as a blocker unless the
  user asked for approval readiness
- verification results and their evidence links
- precedent: the same change already shipped in another repository or
  environment

## Summary

Follow the guide's prefix. Strip tracker keys and commit-type labels from the
change title, keep the scope word when it changes what an approver would check
(the affected area, a feature flag, a rollout phase, a regression reference),
and drop commentary with no deployment consequence.

## Create

- Issue type and project from the profile; summary per the guide.
- Fields: tier, first approver, second approver (when the guide requires it at
  this tier), start date and due date both set to the deployment date, assignee.
- Resolve every field identifier and option value from the create-screen
  metadata of the issue type. The create screen offers a subset of the fields
  visible on an existing ticket; sending a field it does not offer rejects the
  whole request. A field with a similar name may be unrelated.
- No labels, components, or status transitions unless the user asked.
- Body: the guide's title line, then the required sections in the guide's
  order, then links. Every checklist item unchecked.

## Link the work item

Create the relation the guide prescribes between the primary work item and the
approval ticket, in the prescribed direction. Inspect the approval ticket's
existing links first and skip a link that is already present. Do not link
secondary references automatically.

## Read back

The create response does not return everything that was sent. Fetch the ticket
again and compare:

| Check | Expected |
| --- | --- |
| assignee | the intended user |
| first approver, second approver | as collected |
| tier field | the chosen option |
| start date, due date | both equal the deployment date |
| links | the work item in the prescribed relation, exactly once |
| body | each required heading present with a list item on the next line |

If the tracker ignored a value, set it with an edit and read back once more. If a
field cannot be set, report that field by name instead of treating the ticket as
complete.

## Report

- ticket link and key
- tier, assignee, first and second approver
- start and due date
- linked work item
- anything that did not save

The ticket stays in draft state. Requesting approval, sharing the ticket in a
chat channel, and adding comments are separate actions the user must ask for.

## Repairing an automation finding

The automation comments when a ticket enters the approval step with gaps. Its
message may name guide section numbers rather than field names.

| The comment says | It means |
| --- | --- |
| a section number plus "first approver" or "second approver" | a body heading and its list, not a field; do not search for a field with that name |
| a field label | a structured field; set it on the ticket, not in the body |
| "recommended item missing" | a body item that is optional today and may become mandatory; fill it |

Procedure: re-read the guide, map each named item with the table, fix only those
items, run `scripts/check_ticket_body.py` on the revised body, apply the edit,
read back, and report what changed. Do not rewrite unrelated sections while
repairing.
