# Field contract

## Logical fields

The skill and `scripts/check_ticket_fields.py` use these names. Map them to the
tracker's real field keys in the environment profile; the keys never belong in
this repository.

| Logical name | Meaning | Format |
| --- | --- | --- |
| `parent` | the ticket this one hangs under | tracker key |
| `story_points` | relative size on the team scale | integer from the scale, at most the cap |
| `start_date` | planned start | `YYYY-MM-DD` |
| `due_date` | planned finish | `YYYY-MM-DD`, not before the start |
| `estimate_effort` | planned effort in days | multiple of the estimate step, above zero |
| `actual_effort` | measured effort in days | multiple of the actual step, zero allowed |
| `sprint` | iteration, when the team tracks one | optional |
| `container` | true when the ticket only groups leaves | boolean |
| `leaves` | the leaves of a container | list of objects with `key` and `story_points` |

## Required fields by state

| State | Required | May be empty |
| --- | --- | --- |
| `create` | parent, story_points, start_date, due_date, estimate_effort | actual_effort |
| `backlog` | parent | sprint, start_date, due_date; missing points or estimate is a warning |
| `in-progress` | parent, story_points, start_date, due_date, estimate_effort, and sprint when the team uses sprints | actual_effort |
| `done` | everything above plus actual_effort | nothing |

A container has no points of its own. A container that carries points is a
failure, because the total would be counted twice. Its leaves are checked
against the cap individually and summed.

## Estimate and actual are different measurements

Estimate is a judgment made before the work, at a coarse step (half a day is a
common choice). It is not points divided by a constant: tickets with 3 and 5
points may both be half a day, and a 1-point ticket is still at least one step.
When unsure, ask; a guessed estimate pollutes every velocity chart built on it.

Actual is a measurement made after the work, at a finer step (an eighth of a
day is a common choice) so the real cost is preserved. Do not round it up to
the estimate step. Zero is a legitimate actual; an empty field is not.

A mistake worth remembering: a formula meant for actual effort was applied to
estimates, producing fractions the team never uses, and the correction then
rounded actuals to the estimate step as well. Keep the two rules apart.

## Where the values live

Tracker-specific values stay in the environment profile, never in the skill:

```ini
[integration.tracker]
enabled = true
driver = tracker-host-connector
point_scale = 1,3,5
point_cap = 5
estimate_step = 0.5
actual_step = 0.125
require_sprint = false
leaf_issue_type = the standard leaf type, spelled as the tracker reports it untranslated
done_transition = the done transition name used by this project
field_story_points = key from the tracker's field metadata
field_start_date = key from the tracker's field metadata
field_estimate_effort = key from the tracker's field metadata
field_actual_effort = key from the tracker's field metadata
```

The profile doctor reports a driver it has no static checks for as a warning.
Verify the field keys in the active session by reading one existing ticket back
and matching the values you see to the keys you recorded.

## Extracting a ticket for the checker

Read the ticket through the connector, copy each mapped field into a JSON
object under its logical name, and add the target `state`:

```json
{
  "state": "done",
  "parent": "the parent key as the tracker shows it",
  "story_points": 3,
  "start_date": "2026-03-02",
  "due_date": "2026-03-06",
  "estimate_effort": 0.5,
  "actual_effort": 0.625
}
```

Then:

```bash
python3 scripts/check_ticket_fields.py ticket.json
python3 scripts/check_ticket_fields.py --state in-progress --require-sprint ticket.json
python3 scripts/check_ticket_fields.py --scale 1,2,3,5,8 --cap 8 ticket.json
```

The exit code is non-zero when any line is a failure. Warnings never fail the
run; they mark values the user should confirm.
