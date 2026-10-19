# Reading the approval guide

The guide is the single source of truth for what a valid approval ticket looks
like. Read the live document on every run. Do not keep a snapshot in this skill,
in notes, or in an older ticket; snapshots are how rule reversals go unnoticed.

## What the environment profile supplies

These are local facts, not workflow. Take them from the environment profile
(see [the environment-profile skill](../../environment-profile/SKILL.md)) or
ask the user. A missing value is a configuration gap, never permission to infer.

| Fact | Used for |
| --- | --- |
| guide document locator | step 1, read on every run |
| tracker project and issue type for approval tickets | duplicate search and creation |
| field mapping: tier, first approver, second approver, start date, due date | step 5 |
| approver roster per tier, or who to ask | step 2 |
| default tier when the guide allows one | step 2 |
| time zone for date normalization | step 2 |
| relation type that links the work item | step 7 |

## Extraction checklist

Write down each answer before drafting. If the guide does not answer one, ask.

1. Which fields does the automation validate, and what are their allowed values?
2. Which body headings are required? Copy the text exactly, including spacing
   and punctuation.
3. Which items sit under each heading, in which order, and which are mandatory
   versus recommended?
4. Does a lower tier omit a section, or write it with "not applicable"?
5. Who approves at each tier? Is the second approver required to be a different
   person?
6. What summary prefix or title line does the guide prescribe?
7. How must the work item be linked, and in which direction?
8. What changed since the guide's previous revision? Compare the revision date
   with the date of any ticket you are using as content precedent.

## How the automation reads a body

The rules below are the ones that have caused silent rejections. They are the
reason the heading text is copied, not retyped.

- The heading text must equal the guide's text literally. A space moved, a word
  added, a qualifier in parentheses, or a synonym all read as missing.
- The first non-blank line after a required heading must be a list item. An
  explanatory sentence between the heading and the list reads as missing.
- Every required section is written at every tier when the guide says so. The
  second approval *step* may apply only to the top tier; the *writing duty* is
  separate.
- Recommended items that are empty are reported alongside missing mandatory
  ones and can become mandatory for a team without notice. Fill them.
- Checklist items are unchecked at creation. Checked items on an old ticket
  record a verification that happened later; copying them asserts something
  that has not happened.

## Body skeleton

The headings below are illustrative. Replace them with the exact text from the
guide and keep the shape: heading, then list items with answers.

```markdown
# Deployment review

### Schedule

- Deployment date: 2026-03-04 14:00

### First approver checklist

- Target and scope: service, environment, deploy unit, one-line change / links: work item, change
- Change gate evidence: change link, checks, review state, verification results
- Verification: scope, who verified, result counts, evidence links, unverified remainder
- Rollback: method, trigger signal specific to this change, owner
- User exposure: flag or default state, or "no user-visible change"
- Post-deploy check: metric or dashboard, owner, completion criterion
- Residual risk: checked-and-fine items separated from cannot-reproduce items, or "none"
- Incident response: detection, rollback authority, where to share

### Second approver checklist

- Reason second approval applies: tier, critical path, exception, or "not applicable"
- Why now: timing rationale and whether delay is possible
- Remaining risk and why it is acceptable
- Follow-up plan: evidence to collect after approval, or "not needed"

### Post-deploy checklist

- [ ] page loads
- [ ] rendering is intact
- [ ] feature behaves as specified

### Links

- change: the canonical pull request URL, without review anchors or suffixes
- work item: the primary tracker key
```

## Check the draft before creating

Copy the required headings from the guide into a file, one per line, then run:

```bash
python3 scripts/check_ticket_body.py draft.md --headings-file headings.txt
```

or pass each heading on the command line:

```bash
python3 scripts/check_ticket_body.py draft.md \
  --heading "First approver checklist" \
  --heading "Second approver checklist"
```

The script fails on a missing or inexact heading (and names the near miss), a
heading not followed directly by a list item, a duplicated heading, a checked
checklist item, an empty list item under a required heading, and an unfilled
template brace such as `{owner}`. Pass `--allow-checked` only when the guide
asks for a pre-checked item. Pass `--json` for machine-readable output.
