# Selection rules

## Verdicts

| Verdict | Meaning | Destination |
| --- | --- | --- |
| `WRITE` | ready to draft now | radar writing queue; eligible for today's pick |
| `LEARN` | worth it, depth missing | backlog item created with `add`, `status: queued` |
| `LATER` | interest only | radar `Later` list, no item file |
| `PASS` | excluded | radar `Pass` list, one line with the reason |

### `WRITE` requires all of these

- The author can explain the mechanism and its failure modes without reading
  further. When unsure, ask the author one direct question instead of assuming.
- The post can be practical: a checklist, a boundary, a verification or recovery
  procedure, an operating loop. A product tour is not an angle.
- It connects to the blog's recurring subjects as the writing profile records
  them, or the author names the connection.
- The primary source is verified and linked.
- The overlap check returned no confirmed match, or the author confirmed that
  the new angle differs.

### `LEARN` when

- a `WRITE`-shaped topic fails the depth test;
- applying it this week requires study first (an interface, a measurement
  method, a tool);
- the subject is in preview or early rollout and a practical angle needs
  hands-on time first;
- the author says "I do not understand this yet" about a `WRITE` candidate.

### `LATER` when

- there is interest but no link to writing or current work;
- the prerequisite chain is long and nothing in the backlog leads into it.

### `PASS` when

- the item is marketing, hiring, funding, or event news only;
- the only possible post is "this was released";
- no verifiable primary source exists;
- the author has already published the subject and no new angle was found.

## Sources

- The radar README lists sources by category with a kind (`writing`,
  `learning`, or `signal`) and a window in days. Writing sources default to
  seven days and learning sources to fourteen.
- Aggregators and link hubs are `signal` sources. They surface items; they are
  never cited as the source of a candidate.
- Check the date on the primary source. Aggregators resurface old items, and an
  old item is a `LATER` or a `LEARN`, not a timely `WRITE`.
- Record which categories were scanned in the radar frontmatter so a later scan
  knows what was not covered.

## Overlap check

1. Build the published index from the environment profile's blog integration:
   the local content root when the repository is available, otherwise the
   public site's post titles.
2. Run the coarse filter:

   ```bash
   python3 scripts/backlog_report.py overlap --published PUBLISHED_INDEX "candidate title"
   ```

   `PUBLISHED_INDEX` is a text file with one title per line or a directory of
   Markdown posts with `title:` frontmatter. The default threshold is `0.5`
   token overlap.
3. Confirm a reported match by comparing angles, not titles. A different angle
   on a published subject is `WRITE` or `LEARN` with the connection noted; the
   same angle is `PASS`.
4. Also compare against open backlog items and earlier radar entries so the
   same candidate is not re-added every scan.

## Status lifecycle

```text
queued -> in-progress -> done -> draft-ready
                 \-> dropped (any time, user decision)
```

| Transition | Who may make it |
| --- | --- |
| `queued` to `in-progress` | the user, or the agent when the user says they started |
| to `done` | the user's statement that they consumed and understood the source |
| `done` to `draft-ready` | `promote`, after the precondition check passes |
| to `dropped` | the user |

The agent never writes `done` or `draft-ready` from its own reading of the
source. If the agent read the source to help answer a question, the item stays
where it was.

## Staleness

A `queued` item older than the stale window (default thirty days) is surfaced
during `pick` with three choices: schedule it this week, drop it, or keep it
with a one-line reason recorded in the item. Items are never deleted silently.

## Caps

- Five to seven candidates per scan.
- One `WRITE` recommendation per day, at most two `LEARN` per week.
- One radar file per day; a repeated scan updates the same file.
- One backlog item per source; a source with several lessons still gets one
  item, with the lessons listed inside it.
