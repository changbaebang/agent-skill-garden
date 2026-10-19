---
name: production-change-report
description: >-
  Summarizes what reached the production branch during a natural-language
  period and flags lightweight deployment risks from pull-request metadata,
  changed files, and diffs. Use for what shipped last week, production change
  report, release digest, 운영 반영 내역, 지난주 main 변경, 7.24~7.26 변경점.
  Read-only; not for reviewing one pull request or approving a deployment.
---

# Production change report

The report answers "what changed for users and operators, and what could
break" for a period, with a link behind every claim. It reads the code host
and never writes to it, to the tracker, or to chat.

## Resolve the interval before anything else

Resolve the phrase to an exact half-open interval `[start, end)` in one named
time zone and show it at the top of the report. Use the time zone from the
environment profile, otherwise the user's local zone; never leave it implicit.

- Two calendar dates are both inclusive: `7.24~7.26` ends at the start of the
  27th. An explicit time such as `7.22 16:00~7.29 16:00` is kept exactly; never
  round it to whole days.
- "Last 7 days" is a trailing window ending at observation time; "last week"
  is the previous calendar week. The two are not interchangeable.
- An omitted year means the most recent occurrence that is not in the future.
- When wording stays ambiguous, pick the least surprising reading, state it
  prominently, and continue. Ask only when two readings would materially
  change the scope.

`scripts/change_window.py interval` applies these rules deterministically; the
full table is in [references/interval-resolution.md](references/interval-resolution.md).

## Establish the basis

1. Resolve repositories: those the user names, else the current repository,
   else the report scope recorded in the environment profile. Verify each
   production branch live instead of assuming its name.
2. Default basis is **production-branch merge**: pull requests whose base is
   the verified production branch and whose merge time falls inside the
   interval. Open, closed-unmerged, and integration-branch requests are out.
3. When reliable deployment records with deployed revisions exist, prefer
   **production deployment** as the basis: successful deployments inside the
   interval and the revision range they newly shipped.
4. Label the report with the basis used. A merge is never described as a
   confirmed deployment without deployment evidence.

Commands and the deployment-basis derivation are in
[references/evidence-collection.md](references/evidence-collection.md).

## Build the complete change set first

Enumerate every eligible merge before summarizing anything; a digest written
from the first page of results is wrong in a way the reader cannot see. For
each request collect number, title, link, author, base, merge time, merge
revision, body, labels, linked work items, changed files, size, and checks.
Read the diff for anything behaviorally important or ambiguous.

`scripts/change_window.py select` filters an exported request list to the
basis above and marks likely wrappers and reverts.

Handle wrapper requests explicitly. A release, deployment, or
test-branch-to-production merge carries other people's changes:

1. Expand it to its leaf requests or commit range when the evidence allows.
2. Count the wrapper once in the repository total; describe its leaf changes
   without double-counting leaves already merged in the interval.
3. Write `leaf mapping incomplete` when the wrapper cannot be expanded.

Then check net state:

- a change reverted inside the interval is `reverted`, not active behavior;
- a feature flag's observed default matters: `flag off` means code shipped
  without a runtime change, not that risk is zero;
- separate shipping code from later activation, data migration, or campaign
  start;
- group documentation, formatting, tests, and behavior-neutral refactors as
  internal maintenance unless they alter an operational control.

For long periods keep the enumeration complete and deepen diff review in this
order: high-risk signals, broad file changes, unclear bodies, then notable
user-visible changes. Output length is never a reason to drop a payment,
authentication, pricing, routing, API-contract, or rollback change.

## Explain outcomes, not titles

Cluster by user or operational outcome, not by team. Each headline reads:

```text
What changed, as the user or operator experiences it (links)
• core mechanism or cause
• activation condition, limit, rollback, or observation point
```

Merge related requests into one outcome and keep every supporting link. Do not
write "faster" or "safer" without a measurement, and attribute every number to
its source. Keep the top summary to roughly 8 to 12 outcomes and fold the rest
into an internal-maintenance count per repository.

## Assess risk lightly

Levels are `high`, `medium`, `low`, and `hold`; never a numeric probability.
Assign them from [references/risk-signals.md](references/risk-signals.md),
judging the changed behavior and blast radius, not the diff size. For each
high or medium item add one line:

```text
risk: concrete failure mode · mitigation: verified flag/test/fallback/rollback · watch: metric or flow
```

Name a mitigation only when the evidence shows it. Missing diffs, tests, or
deployment data raise uncertainty; they are not proof of a defect. Report at
most five prioritized items and group the rest.

## Report and stop

Render the shape in [references/report-template.md](references/report-template.md)
in the language the user wrote in, and return it in the current session. With
no eligible merges, return the interval, scope, and "no changes"; do not pad
with unrelated open requests.

Posting the report to a chat channel or a document is a separate action that
needs its own request; when asked, use the chat integration from the
environment profile and keep every link intact.

## Quality gate

- every included request merged to the verified production branch inside the
  interval, or the deployment basis is stated;
- interval boundaries, repository counts, merge counts, and no-change counts
  agree with each other;
- wrappers and leaves are not double-counted;
- reverted and flag-off changes are not presented as active behavior;
- every headline and every high or medium risk carries a current link;
- facts, inferences, and unavailable evidence are visibly separated.
