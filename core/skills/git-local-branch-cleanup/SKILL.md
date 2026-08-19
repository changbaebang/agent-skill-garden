---
name: git-local-branch-cleanup
description: >-
  Removes local branches that are old and hold no unique work, judging age
  together with merge and push state rather than age alone. Use for clean up
  local branches, delete stale branches, too many branches, 로컬 브랜치 정리,
  안 쓰는 브랜치 지워줘, or 브랜치가 너무 많아. Never force-deletes, never writes
  to a remote, and never switches branches to make a candidate deletable.
---

# Local branch cleanup

Age alone is not a deletion criterion.

```text
delete = older than cutoff AND (merged OR nothing unpushed)
```

A six-month-old branch holding forty unpushed commits exists only on this
machine. Deleting it leaves the reflog as the sole copy.

## Classify before deleting

Sort every branch into one of three classes and report the counts:

- **tracked and contained** — an upstream exists and the branch adds nothing to it;
- **merged** — no upstream, but the integration branch already contains its work;
- **unique work** — neither holds, so it carries commits found nowhere else.

Report the unique-work class with a per-branch commit count and do not touch it.
Forty commits and one commit call for different decisions, and only the user can
make them.

A branch whose upstream was deleted on the remote does not belong to the tracked
class. The remote copy is gone, so this may be the last one.

## Guards

Never delete the checked-out branch, integration or release branches, shared
deployment or epic branches, backup branches, or any branch whose last commit
was authored by someone else.

An author guard keyed to one configured identity misses branches committed under
an earlier or machine-default identity. It fails toward keeping branches, so the
candidate list is short rather than wrong. Say so instead of widening the guard
silently.

## Delete conservatively

Use the delete that refuses unmerged branches. A refusal means the
classification was wrong, so reclassify and report rather than forcing.

Do not create commits or branches, and do not switch branches, to make a
candidate deletable. Skip it and report it.

## At scale

With hundreds of branches, report an age distribution and the class counts
first, then ask whether to move the cutoff before listing anything.

Use [references/safety-classes.md](references/safety-classes.md) for the
classification commands and the recovery procedure.
