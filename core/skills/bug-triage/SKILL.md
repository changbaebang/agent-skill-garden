---
name: bug-triage
description: >-
  Diagnoses a defect report: reproduction, root cause, fix-ownership verdict,
  history, test cases, approval; never changes code. Use for triage this bug,
  look at this bug, reproduce this, find the root cause, 이 버그 봐줘, 재현되나,
  원인 찾아줘, or 버그 티켓 왔는데. Not for implementing a known fix, feature
  requests, or tracker writes.
---

# Bug triage

The sequence is fixed: reproduce before cause, cause before verdict. A symptom
that reads as a one-line style fix can be a shared base style with many
consumers, introduced by an unrelated change long ago, in a report that names
the wrong platform. Classifying from the symptom alone misses exactly those.

This skill ends at the approval request. It does not edit code, create or
switch branches, merge, or write to the tracker without explicit authorization.

## 0. Entry gate

Stop and tell the user when any check fails:

- The item is a defect report. A feature request goes to `intake` instead.
- The report contains reproduction steps and an expected result. Without them,
  ask the reporter; do not guess a reproduction. A wrong reproduction leads to
  a wrong cause.
- The current repository owns the affected surface.

## 1. Reproduce exactly as written

Follow the numbered steps. Keep the login state, entry path, and device
conditions the reporter gave. For platform-conditional defects (embedded app
webviews, one operating system) a desktop browser on the integration branch
usually shows nothing; load the same page under several client profiles with
[references/profile-matrix.md](references/profile-matrix.md).

"Not reproduced" has two meanings:

| Result | Next |
| --- | --- |
| Reproduced | Step 2 |
| Not reproduced under any browser profile | STOP-A. If the reporter saw it inside an embedded client, first locate which side owns the cause with [references/embedded-client-contract.md](references/embedded-client-contract.md) |
| Reproduced under some profiles only | Not a stop: a signal. Go to step 2 and compare values |

A profile that looks clean may be masked, not fixed: a polyfill or inline
override can write the very value the defect depends on. When one profile
differs, compare the measured values, never just the screenshots.

## 2. Cause

Go down to the line that produces the observed value, not the component that
shows it. Search the integration base ref explicitly; the current checkout may
belong to unrelated work. You have the cause when you can explain in code why
the values diverge between profiles or states. Until then, keep digging.

## 3. Fix-ownership gate, only after the cause is known

Do not use a release risk tier; it measures deployment danger, a different
axis. The question is whether this team can fix it alone.

Gate 1, who fixes: a backend contract change, a native client change (deep
links, bridges, how a webview opens), infrastructure or an external service,
or an undecided product behavior each mean STOP-B. Hand off to the owning team
and end.

Gate 2, who confirms: the code is yours but what is correct must be confirmed
elsewhere. That is STOP-C. Draft the question; steps 4 and 5 continue.

Blast radius: list every consumer of the files a fix would touch, by searching
the repository for their importers or with its dependency-graph tool when one
exists. A shared module used by several applications widens the regression
list; those consumers become regression candidates in step 5.

## 4. History

Find how the code arrived: search the base ref for the problematic string
(`git log -S`) and follow the file through renames. Read the linked change for
the original intent. Check the timeline: a change that landed after the report
date is not the cause. Note later changes that already introduced the tool a
fix would need.

## 5. Record and test cases

Record findings as tracker comments, never by editing the description, and
only when the user authorizes that write. One comment carries cause,
reproduction table, impact, and open questions; the history goes in a separate
comment. Split test cases into new behavior and regression; step 3 consumers
seed the regression list. Mark each case browser-reproducible or device-only.
Hand scenario design to `e2e-test-design` when it is installed.

## 6. Approval

Report steps 3 to 5 together and ask whether to proceed:

- cause in one line with file and line evidence;
- gate verdict: this team alone, or waiting on which confirmation;
- blast radius: consumer count and regression targets;
- test-case counts: new, regression, device-only;
- what remains unconfirmed.

On approval, hand off to `ticket-to-pull-request`, which runs `work-start` as
its preflight. Branch creation belongs there.

## Stop states

A stop written as a bare notice kills the flow. Each one records what is
awaited, who unblocks it, and where work resumes.

| | When | Awaiting | Resume |
| --- | --- | --- | --- |
| STOP-A | No browser reproduction | Device or app confirmation | Step 1 once the reporter narrows the conditions |
| STOP-B | Not fixable by this team alone | The owning team's decision | Hand off; this flow ends |
| STOP-C | Judgement needs outside confirmation | The other team's answer | Step 3 gate 2; steps 4 and 5 run meanwhile |

## Never

- change code, or create, switch, or delete branches;
- merge pull requests;
- reproduce from guesswork when steps are missing;
- call a report simple before the cause is known;
- treat a single clean platform as proof that nothing is wrong there.

Templates for the comments, the stop notice, and the approval report are in
[references/triage-report.md](references/triage-report.md).
