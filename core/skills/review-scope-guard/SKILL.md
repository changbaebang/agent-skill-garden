---
name: review-scope-guard
description: >-
  Measures how far a change reaches before reviewing its lines: a shared base
  style, default, global selector, or override hits every consumer while the
  diff shows one line. Use for blast radius, how far does this change go,
  review scope, 변경 반경, 영향 범위, or 이 한 줄 어디까지 가나. Not for bug
  hunting; posts nothing unless asked.
---

# Review scope guard

Review time grows with the diff; damage grows with reach. One line inside a
shared base style, a default variant, or a global selector is one line in the
diff and every consumer in production. Three pull requests over a year can each
pass review and still combine into a defect visible on one platform only: a
spacing fix added to a shared base instead of the one screen the ticket named;
a later fix for another platform that zeroed the same value and hid the
symptom; a refined condition whose migration skipped the shared component. Each
diff was correct on its own lines. The reviewer's field of view was the diff,
and the defect lived outside it.

This skill pulls the outside in as numbers, asks five questions only when the
numbers justify them, and leaves the answers where the next reviewer will see
them. It does not hunt bugs and does not edit code.

## 1. Count the reach before asking anything

Run the counter from inside the repository, with a diff base or explicit files:

```bash
node scripts/blast_radius.mjs --diff                 # against the default branch
node scripts/blast_radius.mjs --diff origin/develop  # against a named base
node scripts/blast_radius.mjs src/shared/Button.tsx  # whole files, no diff
node scripts/blast_radius.mjs --diff --all           # every touched file
```

It reports three things per changed source file, read from the committed tree:

| Block | Meaning | When it appears |
| --- | --- | --- |
| consumers | files that reference an exported symbol the change touched, plus workspace packages that depend on the owning package | quote the number in the request |
| cannot opt out | `base:` styles, `defaultVariants`, `defaultProps`, `:root` / `html` / `body`, `@layer base` | Q1 and Q2 are mandatory |
| overrides a value | `style.setProperty`, `!important`, `documentElement.style`, library `.defaults`, `Object.assign` on a global | Q4 is mandatory |

The default output shows flagged files only. A two-hundred-file diff that
touches shared exports in forty of them must not bury the two dangerous lines
under forty consumer lists; drowning the signal is the failure this skill exists
to prevent. With no flags it shows the three widest consumer lists for
orientation. Counts are upper bounds: a common symbol name inflates them, so
confirm with the sample paths before quoting a number.

No flags and no consumers: stop here and return to ordinary review. Do not run
the questions on a change that reaches nowhere; a ritual that runs every time is
a ritual nobody reads.

## 2. Five questions, only for flagged changes

Answer each in writing. An answer that stays in chat is asked again by the next
person.

**Q1. How many places does this line apply to?** Quote the counted number. A
one-line change and a thirteen-screen change deserve different review time.
Name at least one consumer that should not receive the change; if none can be
named, the list has not been read. Pass: the consumer list was read and every
consumer is meant to change.

**Q2. Does the diff's scope match the ticket's scope?** A ticket about one
screen with a diff in a shared layer is a mismatch. Either the request says why
the change belongs in the shared layer, or the change moves to the consumer.
Pass: someone who reads only the ticket title can predict the diff's reach.

**Q3. Is the condition named correctly?** When a branch is added or narrowed,
read the predicate's name, not its value. Reviews often say "narrow this" and
rarely say to what. Search the repository for an existing predicate that states
the exact condition first; the precise one is often already there and unused.
Two predicates that both return a boolean look identical to the type checker.
Pass: the predicate's name read aloud matches the intent.

**Q4. Does this fix the cause or hide the observation?** For every override
ask: if this override were removed, what would become visible again? No answer
means the cause is unknown and the symptom will persist on another platform or
screen. Check that the override is no wider than the ticket: a bottom-edge
ticket that zeroes the top edge too hides somebody else's defect for a year.
Pass: the value before and after the override can be stated per platform.

**Q5. If a predicate was refined, where is the migration list?** A request that
splits one concept into two attaches a list of every old consumer, each marked
migrated or kept, with the reason for every kept entry. A signature change is
caught by types; a concept refinement is not. Pass: every old call site is
counted and classified.

## 3. Leave the record on the pull request

The deliverable is a reach block that reviewers see when they open the request,
not a summary in chat; a spoken number disappears. Draft it with
[references/reach-block.md](references/reach-block.md): the counted reach, the
dependent packages, and one row per question. Keep rows that do not apply and
write "not applicable"; an empty cell and a checked cell are different things.

Posting is an external write. Present the block, then post it as a comment when
the user asks. When appending to the description instead, read the current body
first and append to it, because a body edit replaces the whole text. If no
request exists yet, keep the block and say it goes into the description at
creation. If the block is neither posted nor kept, say so plainly: the reach is
unrecorded.

## 4. What this skill does not do

- Find bugs. Logic errors, null handling, and performance belong to a critical
  or domain review pass.
- Change code. It measures and records.
- Trace runtime paths, caches, flags, or auth. That is a side-effect trace; this
  skill measures static reach and scope fit.
- Run the five questions on an unflagged change.

Script options, exit codes, and output shape:
[references/counting-reach.md](references/counting-reach.md).
