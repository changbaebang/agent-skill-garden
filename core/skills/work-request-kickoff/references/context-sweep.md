# Context sweep and owner evidence

The anchor message is where the request was noticed, not where it was decided.
Run the sweep below before writing a single line of the definition.

## Search plan

Run these in parallel where the host allows.

| Step | Where | Query | Purpose |
| --- | --- | --- | --- |
| A | chat search | the work's name, its distinctive nouns, the tracker key | related threads and announcements |
| B | chat search | each candidate owner's messages filtered by the same keywords | what that person actually committed to |
| C | anchor channel | messages before and after the anchor | the conversation the anchor replied to |
| D | user directory | names and handles that appear in the thread | the identifiers a mention needs |
| E | tracker | every key the thread or the search surfaced | assignee, state, description, comments |
| F | documents | every page the tracker item or the thread links | the written scope, if any |
| G | repository | docs the item or the thread names, then a read-only scan for the named components | what already exists |

Record where each fact came from. A fact with no source is an assumption and is
labelled as one in the definition.

## Stop condition

Stop collecting when all three hold:

- two or three threads on the same topic have been read;
- the tracker item has been opened, or the thread confirms there is none;
- the owner candidates are down to two or fewer.

When one of them cannot be reached, ask the user one question that would settle
it. Do not keep searching to avoid asking, and do not ask three questions where
one would do.

## Owner evidence, strongest first

| Rank | Evidence | Typical wording |
| --- | --- | --- |
| 1 | Committed in the thread to a schedule, deliverable, or hand-off | "I'll have the plan on Thursday", "I'll take the download" |
| 2 | Tracker assignee, or named as implementer in the thread | assignee field; "X is implementing this" |
| 3 | Named as owner of the goal or feature the request belongs to | an objective list, a feature ownership table |
| 4 | Mentioned without a role | a bare mention |

Use the highest rank that has evidence. A rank-4 mention never beats a rank-1
commitment, even when the mentioned person is more senior or more active.

Confidence in the candidate table:

- **high**: rank 1 or 2 evidence from the anchor thread itself;
- **medium**: rank 2 or 3 evidence from a related thread or the tracker only;
- **low**: rank 4, or conflicting evidence between sources.

Two high-confidence candidates with different roles (one schedules, one
implements) are not a tie; present both with their roles. Two candidates with
the same role and the same confidence are a tie; ask the user one sentence.

## What a reply changes

When the owner answers, compare the thread against the earlier definition and
list each delta explicitly:

- a date moved, with the old and new value;
- the tracker item or a document was updated, and what it now says;
- a meeting or invite was offered, and where it lives;
- the owner changed, or a second person was pulled in.

A calendar invite is a time only after it has been read from the calendar
through a tool the environment provides. Phrases such as "later today" stay as
phrases in the definition.

## Environment profile values

This workflow needs no fixed channel, workspace, or tracker host. When a team
has a standing channel for kickoff requests, keep its alias in the chat section
of the environment profile and read it from there. A configured alias names a
destination; it never authorizes a send.
