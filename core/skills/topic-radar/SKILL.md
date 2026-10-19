---
name: topic-radar
description: >-
  Curates writing and learning topic candidates from configured sources into a
  dated radar and a learning backlog kept apart from drafts, then promotes
  learned items into draft input. Use for topic radar, what should I write
  about, blog ideas, learning backlog, study queue, 블로그 주제, 배울 것 정리, or
  promote this topic. Not for drafting, polishing, or publishing posts.
---

# Topic radar

Choose one mode: `scan`, `add`, `pick`, `done`, or `promote`. The radar decides
what to write next and what to learn first. It never writes a post, and it
never advances a learning item on the agent's own judgment.

## Two queues, one depth gate

Every candidate ends in exactly one place:

- **writing queue** (`WRITE`): the author can already explain the mechanism and
  its failure modes, a practical angle exists, and no published post covers it;
- **learning backlog** (`LEARN`): the topic is worth it, but the author has not
  consumed or understood the primary source yet;
- `LATER` or `PASS`: interest without a connection, or nothing to add.

The gate between the queues is depth, not interest. A `WRITE` verdict on a
topic the author does not yet understand produces a survey post that restates
the announcement. When depth is missing, the correct output is a backlog item,
not a draft. Read [references/selection-rules.md](references/selection-rules.md)
before classifying.

## Resolve locations, do not guess them

The radar root, its `items/` directory, the drafts destination, and the
published-post index are local facts. Take the drafts path and public site from
the environment profile's blog integration when one is enabled; take the rest
from the radar root's `README.md`. When a location is missing, ask once and
record the answer there. Keep the radar and backlog outside the drafts
directory so a publication step can never mistake a candidate list for a post.

## Scan

1. Collect items inside the window (default seven days for writing sources,
   fourteen for learning sources) from the sources listed in the radar README.
2. Treat aggregator and link-hub feeds as signals only. Resolve each item to its
   primary source (official post, release note, paper, recorded talk) before it
   may become a candidate, and cite the primary source, never the aggregator.
   An item whose primary source cannot be verified is `PASS`.
3. Check overlap against published posts and existing backlog items before
   ranking, starting with `scripts/backlog_report.py overlap`. Confirmed
   overlap is `PASS`, or `LEARN` when a genuinely new angle still needs depth.
4. Keep five to seven candidates. Give each a verdict, a one-line reader
   benefit, an angle, the overlap result, and the primary link.
5. Write or update today's radar file from
   [references/radar-templates.md](references/radar-templates.md). One file per
   day: a second scan on the same day updates it instead of adding another.
6. Recommend exactly one `WRITE` for today and at most two `LEARN` for the week.
   More than that is a news digest, which is the failure this skill prevents.

## Add

Create one backlog item per source. Fetch only the title and format metadata;
do not read the article or transcribe the video to produce a summary, because
an agent summary stored in the item would later pass as the author's learning.
Start at `status: queued`, attach one or two areas from the README, and add a
row to the README index.

## Pick

Read the latest radar and the backlog summary:

```bash
python3 scripts/backlog_report.py summary RADAR_ROOT
```

Fix one `WRITE` candidate as today's recommendation with a title, slug, angle,
and an opening hook of a few sentences. Name one or two `LEARN` items for the
week, preferring queued items that have gone stale and items the latest radar
flagged as blocked on depth. Pick updates the recommendation section of the
radar file only.

## Done

Move an item to `done` only when the user states they consumed and understood
the source. Record the takeaways, where they apply, and what remains unclear in
the user's words. A summary the agent produced does not count as learning, and
the agent never sets `done` or `draft-ready` on its own.

## Promote

Promotion turns a learned item into draft input. Check preconditions first:

```bash
python3 scripts/backlog_report.py promote-check RADAR_ROOT/items/ITEM.md
```

The item must be `done` or `draft-ready`, carry a draft slug, and have filled
takeaways and a draft angle. When the check passes, create a draft skeleton in
the drafts destination with a back-reference to the item, set the item to
`draft-ready`, and hand off to the blog writing workflow. The skeleton is input
for drafting, not a draft to polish or publish; the writing skill's own voice
profile and publication gate apply from here.

## Write boundary

Each mode writes only the files it names: the radar file, backlog items and the
README index, and a promoted skeleton in the drafts directory. Nothing here
commits, pushes, publishes, posts to a channel, or edits an existing draft.
Status transitions to `done` and `draft-ready` require the user's statement in
the current conversation.

## Report

End every mode with the result block from the templates: mode, paths touched,
verdict or status counts, the recommendation, and the single next step, which is
a radar or backlog action or a hand-off to drafting. Do not restate every
candidate in chat; the radar file holds them.
