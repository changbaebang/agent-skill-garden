# Radar templates

All dates are the user's local calendar date. When the user names a date, use
it. File names are `YYYY-MM-DD-<slug>.md` with a kebab-case slug.

## Radar root layout

```text
RADAR_ROOT/
  README.md                  locations, sources, areas, item index
  radar/YYYY-MM-DD-radar.md  one scan result per day
  items/YYYY-MM-DD-slug.md   one learning item per source
```

The drafts destination lives elsewhere, as the environment profile's blog
integration records it. Radar and backlog files are never placed inside it.

## README template

```markdown
# Topic radar root

## Locations
- drafts destination: taken from the environment profile when enabled
- published index: local posts directory or public site used for overlap checks

## Sources
| Category | Kind | Window (days) | Feed |
| --- | --- | --- | --- |
| web-platform | writing | 7 | official blog or release feed |
| research-talks | learning | 14 | conference channel or paper feed |
| link-hub | signal | 14 | aggregator; resolve every item to its primary source |

## Areas
| Area | Covers |
| --- | --- |
| web-performance | measurement, budgets, regressions |
| agent-operations | automation boundaries, verification loops |

## Items
| Added | Slug | Area | Status | Draft slug |
| --- | --- | --- | --- | --- |
```

Categories and areas are the user's own vocabulary; the rows above are only
shape examples to replace.

## Radar file template

```markdown
---
type: topic-radar
date: YYYY-MM-DD
sources_scanned: [web-platform, research-talks, link-hub]
---

# Topic radar — YYYY-MM-DD

## Summary
- scanned: categories and windows
- candidates: N (WRITE a / LEARN b / LATER c / PASS d)
- write today: title
- learn this week: one or two item slugs

## Write today
- title:
- why now:
- angle: guide | checklist | boundary | retrospective
- slug:
- opening hook: three sentences at most
- next: hand the slug to the blog writing workflow's draft mode

## Candidates
| Verdict | Topic | Reader benefit | Angle | Overlap | Primary source |
| --- | --- | --- | --- | --- | --- |

## Learn this week
| Item | Area | Why now | Source |
| --- | --- | --- | --- |

## Later
- topic — why it waits

## Pass
- topic — reason

## Waiting for promotion
| Item | Status | Draft slug | Next |
| --- | --- | --- | --- |
```

## Item file template

```markdown
---
type: learn-item
title: "TITLE"
source: "URL"
source_type: video | article | paper | course | talk
area: [web-performance]
status: queued
added: YYYY-MM-DD
draft_slug: ""
---

# TITLE

## Why learn
- one to three sentences linking the source to writing or current work

## Source
- link, format, estimated time when known

## After learning
- takeaways:
- apply where:
- still unclear:

## Draft angle
- title candidates:
- shape: guide | checklist | curation | retrospective
- draft_slug:
```

`After learning` is filled only from the user's own account. `Draft angle` may
be sketched at `add` time and revised at `done`. `promote-check` treats a
label with nothing after the colon as unfilled.

## Promoted skeleton template

Follow the blog's own frontmatter contract from the writing profile; the fields
below are the minimum the skeleton carries.

```markdown
---
title: "TITLE from the item's draft angle"
date: YYYY-MM-DD
tags: []
learn_source: items/YYYY-MM-DD-slug.md
---

> Promoted from the learning backlog. Source: [TITLE](URL)

## Summary
- three or four bullets from the item's takeaways, in the author's words

## Background
- why this was worth learning and what the source established

## Sections from the draft angle
- headings only; the writing workflow fills them
```

After writing the skeleton, set the item's `status: draft-ready` and
`draft_slug`, update the README index row, and stop. Drafting, polishing, and
publication belong to the blog writing workflow.

## Result block

```markdown
## Result
- mode: scan | add | pick | done | promote
- paths: files created or updated
- counts: WRITE n / LEARN n / LATER n / PASS n, or status counts
- recommendation: one title, or none

## Next
- the single next action
```
