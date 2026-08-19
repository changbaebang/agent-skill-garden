---
name: git-remote-branch-cleanup
description: >-
  Deletes remote branches whose pull requests are merged or closed, after
  measuring what each deletion would actually lose. Use for clean up remote
  branches, delete merged branches, closed pull request branches, 원격 브랜치 정리,
  리모트 브랜치 정리, or 머지된 브랜치 지워줘. Dry-run by default, deletes only what
  the user approves, and never touches shared branches or other people's work.
---

# Remote branch cleanup

Deleting a remote branch has no reflog behind it. Treat every run as a dry run
until the user approves specific branches.

## Guards are evaluated before pull-request state

Exclude a branch when any of these holds, without exception:

- it is an integration, release, staging, or QA branch;
- it is a shared deployment or epic branch others may be stacking on;
- its last commit was authored or committed by someone else;
- its pull request is open;
- it has no pull request at all, so it is someone's work in progress;
- it is the repository default branch.

Name guards must come first. A long-lived shared branch can still be attached to
an old closed pull request, so a rule that reads only pull-request state will
delete a live branch that is far ahead of the integration branch. That single
ordering mistake is the difference between cleanup and an outage.

## Two classes, not one

**Merged** branches are already contained in the base. Nothing is lost, so the
list can be approved as a group.

**Closed but unmerged** branches hold commits that exist nowhere else. Confirm
these one at a time, never as a batch.

Merged branches are usually gone already on hosts that delete on merge. An empty
merged list is the expected result, not a failure, and it means the check need
not be repeated.

## Measure the loss correctly

Counting revisions between base and branch, or diffing the two, both overstate
the loss badly. The first counts commits that arrived by merging the base into
the branch; the second counts everything the base has done since. Reported
unchecked, they either frighten the user out of cleaning up or suggest the
branch is corrupt.

Compare by patch identity instead. It reports only commits whose content is
absent from the base and it recognizes squashed merges. Show that count with the
last commit date and author for every closed candidate. It is the only basis the
user has for deciding.

## Record recovery, then delete

Capture each branch tip revision to a file and tell the user the path, so a
deleted branch can be restored by pushing that revision back. Delete approved
branches one at a time, continue past failures, and report failures at the end.

Report what was deleted, what a guard skipped and why, and the recovery file
path. Do not relax a guard for a single run.

Use [references/loss-measurement.md](references/loss-measurement.md) for the
commands and the recovery procedure.
