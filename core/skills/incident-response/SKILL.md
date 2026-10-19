---
name: incident-response
description: >-
  Runs the incident lifecycle: declare, respond in a named role, resolve, and
  write the postmortem, with optional critical-page sweep and risk forecast.
  Use for incident, outage, on-call, postmortem, 장애 대응, 장애 선언, 장애 회고,
  재발 방지. Drafts only; never posts, declares, or changes tracker state. Not
  for ordinary bug fixes.
---

# Incident response

An incident runs in two places: the incident channel and the tracker record.
Everything this skill produces is a draft for the person to post, declare, or
file. Confirmed facts leave the incident channel; inferences do not.

## Find the stage first

| Situation | Stage | Read |
| --- | --- | --- |
| Something looks wrong; unclear whether it is an incident | recognize | [declaration.md](references/declaration.md) |
| It is an incident; no channel or record exists yet | declare | [declaration.md](references/declaration.md) |
| A channel exists and recovery is under way | respond | [response.md](references/response.md) |
| Recovery is agreed or the channel is marked resolved | resolve | [closure.md](references/closure.md) |
| Root cause, prevention actions, or the write-up are due | postmortem | [closure.md](references/closure.md) |
| The suspected impact is a page that will not render | sweep (optional) | [page-sweep.md](references/page-sweep.md) |
| Someone asks what is likely to break next week | forecast (optional) | [forecast.md](references/forecast.md) |

Jump to the stage. Do not walk a person who is mid-recovery through
declaration, and do not open a postmortem while the channel is still open.

## Rules that hold in every stage

- **Recovery before cause.** Roll back, disable the new change, or cut the
  traffic first. Root cause analysis starts after recovery.
- **Separate fact from inference** and label each. Only confirmed facts go to
  the wider announcement channel.
- **Acknowledge within a minute** when on call. Silence reads as nobody looking.
- **Never invent channel content.** What was not read is marked unverified.
- **Mask personal data,** order identifiers, and customer contact details in
  every draft, including the postmortem.

## Gather before writing

1. Normalize the reference: `python3 scripts/incident_ref.py "<key, channel, or link>"`,
   passing `--project` and `--channel-prefix` from the environment profile when
   the convention differs. It returns what to look up and performs no lookup.
2. Read the incident channel: topic (resolved or not), pinned messages, and the
   last 50 to 100 messages. Then read the tracker record.
3. Search past incidents for the same service or symptom. Carry one lesson per
   match, not the whole history.
4. Fill the checklist in [response.md](references/response.md). A field that
   cannot be filled is reported as unknown, not guessed.

A missing source is a gap to report, never evidence that nothing happened.

## Declare

Thirty seconds before declaring: is it an incident, not a one-off spike, a
single user, or something already recovered; what is the one-line impact; is
the owning service known. Score the declaration with the rubric in
[declaration.md](references/declaration.md). Below 70 means the impact or title
needs one more line, or the incident itself needs a second opinion.

A title names the service, the symptom, and the scope. "Something is broken"
and "urgent, please check" are not titles.

After declaring: enter the channel, acknowledge, agree who is commander,
communications lead, and operations lead (one person may hold two), and post
the first status update within fifteen minutes.

## Respond

Three roles, three ten-minute cards; see [response.md](references/response.md).
The commander names the goal and the single decision point and fixes the
update cadence. The communications lead publishes confirmed impact, status,
and next update time outside the channel. The operations lead executes the
fastest recovery path and shares verification evidence. The usual failure is
one person holding all three without saying so; make the roles explicit in the
channel when they are not.

Situation analysis follows one shape: summary, timeline in the team's declared
time zone, impact, current state, similar past incidents, prioritized next
actions, and a status-update draft. Use the signal table in the reference to go
from symptom to first action. The first action is almost always a rollback,
disabling the new change, or a traffic cut, not an investigation.

## Resolve

When the channel marks recovery or the responders agree on it, draft the
resolution announcement and classify follow-ups as short, medium, or long
term, each with an owner, a deadline, and a metric that shows it worked.
Templates are in [closure.md](references/closure.md). A follow-up without a
metric is a wish.

## Postmortem

Write only what the channel and the tracker support. A 5 Whys step with no
evidence is marked unverified, not filled in. Prevention actions must be
measurable: a monitor, a test gate, a contract check, a runbook step. Before
finishing, list the follow-ups still in progress from earlier incidents so the
new ones neither duplicate nor contradict them.

## Optional: critical page sweep

When the impact may be client-side, open a fixed representative set of pages
read-only and classify each as pass, degraded, fail, login required, blocked
fixture, flow required, or not web. Then read the pattern: many applications
failing points at a shared shell or gateway, one application at its deployment,
one route at that route. Never change state on a page and never declare from
the sweep alone; correlate with the monitoring dashboards first. See
[page-sweep.md](references/page-sweep.md).

## Optional: weekly risk forecast

A personal, read-only forecast of what is most likely to fail next week, scored
deterministically with `scripts/risk_score.py` and graded after the week ends.
It ranks attention; it is not a probability. See
[forecast.md](references/forecast.md).

## Write boundary

This skill never posts to a channel, declares an incident, creates or
transitions a tracker record, or changes monitoring. It returns drafts and the
person decides what goes out. Channel naming, the tracker project, dashboard
locations, and the representative page list come from the environment profile.
