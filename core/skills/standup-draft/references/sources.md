# Sources and the evidence file

Every query below is a read. The values it needs (channel alias, saved tracker
filter, code-host account, transcript roots, drafts folder) come from the
environment profile or from asking the user once. Do not copy them into this
skill or into a shared skill body.

## Chat: the previous standup thread

| Read | Yields |
| --- | --- |
| the user's own reply in the previous thread | yesterday's "next" list, which becomes `previous_next` |
| colleagues' replies in the same thread | section labels, bullet glyphs, key style for `format`; never content |
| today's thread parent, when it exists | on-call duty and announcements for the `next` free list |

Search the standup channel for the greeting the team's bot or facilitator posts,
sorted newest first, and take the most recent thread older than today. Its date
is `previous_report_date`. If the user did not reply in that thread, say so in
the evidence table and skip the carry-over check rather than guessing.

## Code host: the user's pull requests

Query pull requests authored by the user and updated on or after the window
start. Classify by state:

| State | Section | Evidence string |
| --- | --- | --- |
| merged inside the window | done | `pr #N merged` |
| open, updated inside the window | next | `pr #N open` |
| closed without merge | neither; mention only if the user asks | `pr #N closed` |

Query reviews the user submitted in the same window separately and pass them
as `role: reviewer` records. They collapse into a single done line.

## Tracker: items assigned to the user

Query items assigned to the user and updated within the window, newest first.

| Observation | Section |
| --- | --- |
| status moved to a done category inside the window | done |
| comment or status change inside the window, item still active | done (as progress) and next |
| in progress, no change inside the window | next |
| blocked, waiting on another team, or dependency with no owner | blockers, phrased as "confirm schedule or owner" |

When the draft's "next" has no confirmed items, run the user's saved
assignment filter from the profile; fall back to "assigned to me and not
resolved" when no filter is configured. Pass the results as `issues` and let the
script list up to five keys under "Open assignments". Add the tracker links from
the profile's base address when presenting them; the script prints keys only.

## Local sessions

Agent transcripts whose modification time falls in the window. Skim for work
topics (implementation, review, incident follow-up, writing) and pass each as a
`sessions` record with a one-line `topic` and any tracker keys it names. Leave
out personal, sensitive, or exploratory conversation. Transcript roots are host
specific; the audit script in
[skill-usage-audit](../../skill-usage-audit/SKILL.md) documents the usual ones
and accepts overrides.

## The evidence file

`scripts/standup_draft.py draft --input evidence.json` consumes this shape.
Every field except `report_date` is optional; absent sources are reported as
gaps.

```json
{
  "report_date": "2026-05-21",
  "previous_report_date": "2026-05-20",
  "previous_next": [
    "Land the checkout retry fix (ABC-12)",
    "Monitor the release after deploy"
  ],
  "format": {
    "labels": {"done": "Done", "next": "Next", "blockers": "Blockers"},
    "bullet": "-"
  },
  "pull_requests": [
    {"number": 101, "title": "Retry failed checkout submits", "state": "merged",
     "updated_at": "2026-05-20T10:12:00Z", "role": "author"},
    {"number": 104, "title": "Split the cart hook", "state": "open",
     "updated_at": "2026-05-20T17:40:00Z", "role": "author"},
    {"number": 97, "title": "Fix locale fallback", "state": "merged",
     "updated_at": "2026-05-20T09:00:00Z", "role": "reviewer"}
  ],
  "issues": [
    {"key": "ABC-12", "summary": "Checkout retry", "status": "Done",
     "status_category": "done", "updated_at": "2026-05-20T11:00:00Z"},
    {"key": "ABC-15", "summary": "Cart hook split", "status": "In Progress",
     "status_category": "in_progress", "updated_at": "2026-05-20T17:45:00Z"},
    {"key": "ABC-20", "summary": "Promo banner contract", "status": "Blocked",
     "status_category": "in_progress", "blocked": true,
     "blocked_reason": "waiting on the backend contract", "updated_at": "2026-05-19T09:00:00Z"}
  ],
  "sessions": [
    {"topic": "Refactored the retry helper", "at": "2026-05-20T15:00:00Z", "keys": ["ABC-12"]}
  ],
  "next": ["On-call this week"],
  "blockers": [],
  "gaps": ["chat: previous thread had no reply from me"]
}
```

Field notes:

- `status_category` is one of `done`, `in_progress`, `todo`. Map the tracker's
  own status names onto these three before writing the file.
- Timestamps are ISO-8601; only the date part is compared against the window.
- `keys` are taken from the text when omitted. Any token shaped like an upper
  case project prefix, a hyphen, and digits counts as a key.
- `next` and `blockers` are free lists for facts a source stated that the
  record shapes above cannot carry, such as on-call duty from the thread
  parent. They are rendered as stated, with `chat` as their evidence.
- `gaps` are rendered at the end so the reader knows what was not checked.
