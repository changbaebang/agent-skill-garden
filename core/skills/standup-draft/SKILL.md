---
name: standup-draft
description: >-
  Drafts a daily standup (done, next, blockers) from the previous standup thread,
  your pull requests, tracker items, and local agent sessions, with evidence per
  line. Use for standup draft, daily update, what did I do yesterday, 스탠드업 초안,
  데일리, 한일 할일. Read-only. Not for posting to chat, editing the tracker, or
  weekly/sprint reports.
---

# Standup draft

The result is text the person pastes into the standup thread after reading it.
Nothing this skill produces is sent, scheduled, or filed on their behalf.

## Fix the window first

The report date is today unless the user names a date. "Done" covers the span
from the previous standup to the report date; by default that is yesterday
through this morning. When the previous standup thread is older than one day
(a weekend, a holiday, a missed day), widen the done window back to that
thread rather than leaving the gap unreported.

```bash
python3 scripts/standup_draft.py window --date YYYY-MM-DD --previous YYYY-MM-DD
```

## Collect read-only, in parallel

Every source is read, never written. A source that cannot be read is recorded
as a gap in the evidence table, not rendered as an empty section.

1. **Chat.** Open the previous standup thread in the channel the environment
   profile names for standups. Take the user's own last reply: its "next" list
   is today's carry-over check. Take colleagues' replies for format and tone
   only, never for content. If today's thread already exists, read only the
   parent message for on-call duty and announcements.
2. **Code host.** Pull requests the user authored, updated inside the window:
   merged ones are done, open ones with recent activity are next. Reviews the
   user gave collapse into one done line, "reviewed N pull requests".
3. **Tracker.** Items assigned to the user and updated inside the window. A
   status change or comment in the window is done; an in-progress item is
   next; an item waiting on someone else, or a dependency with no owner, is a
   blocker phrased as "confirm schedule or owner", not as a guess at the cause.
4. **Local sessions.** Agent transcripts modified inside the window, read for
   work topics only. Skip anything personal or sensitive. A session is weak
   evidence on its own and is marked low confidence unless another source
   agrees.
5. **Recent closeouts.** If the user ran a work-start or work-closeout flow in
   the window, those items lead the respective section.

Channel alias, tracker filter, code-host account, and transcript roots come
from the environment profile or are asked once; none of them belongs in this
skill. Query shapes are in [references/sources.md](references/sources.md).

## Cross-check before writing

- Does every item in yesterday's "next" appear in today's "done"? Each one
  that does not is either carried into "next" again, marked as such, or raised
  as a question to the user. It is never silently dropped.
- Does every pull request merged in the window appear in "done"?
- Does every "done" line cite at least one source? Session-only lines are low
  confidence.
- Is every blocker stated by a source? Blockers are never inferred.

Put the collected records in the JSON shape described in the reference and let
the script assemble the draft, the evidence table, and the carry-over check:

```bash
python3 scripts/standup_draft.py draft --input evidence.json
```

The script decides nothing about what to collect; it classifies, de-duplicates
by tracker key, orders "next" by priority, and scores confidence.

## Write

- **Done**: finished, merged, deployed, QA handled, reviewed, monitored.
- **Next**, in this order: yesterday's unfinished "next", tracker items in
  progress, open pull requests, then meetings and on-call duty.
- **Blockers**: blockers, unconfirmed schedules, release bundling, waiting on
  another team. Omit the section when no source reports one.
- Three to seven one-line bullets per section. Mirror the labels, bullet glyphs,
  and key style the previous thread already uses; do not impose a template on
  a team that has one.
- When "next" is empty, say so in one line and list up to five open assigned
  items as links for the person to choose from. Do not manufacture bullets.

## Deliver

Return the draft in the conversation using
[references/output-template.md](references/output-template.md): the banner
that it was not posted, the three sections, then the evidence table, per
section confidence, and the carry-over check. Saving a copy to a local drafts
folder from the profile is allowed; nothing leaves the machine.

Never send, schedule, or stage a chat message; never react or reply in the
thread; never create, edit, or transition a tracker item; never comment on or
review a pull request. A request for a standup draft authorizes none of these,
and neither does the standup channel being configured.

## Learn from what was actually posted

When the user pastes the version they posted, summarize the difference
(missing, excess, tone), and offer one line for their local preference notes
after they confirm it. Do not store it in this skill or send it anywhere.
