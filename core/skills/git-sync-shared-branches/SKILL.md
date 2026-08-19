---
name: git-sync-shared-branches
description: >-
  Brings local copies of shared branches such as integration, staging, and QA
  up to the remote, and stops when a local copy holds commits the remote does
  not. Use for sync shared branches, update local main, match the remote,
  공유 브랜치 최신화, main stage qa 동기화, or 원격 기준으로 맞춰줘. Never pushes,
  never force-updates a remote, and never stashes automatically.
---

# Shared branch sync

The remote is the source of truth and the local copy follows it. History moves
in one direction only.

## Preconditions

Fetch with pruning, then confirm the working tree is clean and note the current
branch. Stop on a dirty tree and let the user choose between committing and
stashing.

Do not stash automatically. A stash can revert paths outside the intended
pathspec and restore only part of them, which turns a sync into data loss.

## Decide per branch

Compare each target against its remote counterpart.

- The local copy adds nothing: bring it up to date.
- The local copy adds commits: **stop**. Report how many and which, and let the
  user decide. This is the only dangerous step in the skill, because overwriting
  here leaves the reflog as the only copy.
- No local branch exists: create it tracking the remote.

## Update without disturbing work

For the checked-out branch, allow only a fast-forward, so a failure surfaces the
ahead case instead of silently rewriting it.

For every other branch, move the reference directly rather than checking it out
and resetting. The working tree is never touched, so the branch the user is
actually working on is unaffected.

## Report

List each branch with its old and new revision, or the reason it was skipped.
Call out skipped branches separately so they are not buried under successes.

Default targets are the integration, staging, and QA branches. Shared deployment
branches are excluded by default because other people may be stacking work on
them; include one only when the user names it.

Use [references/sync-matrix.md](references/sync-matrix.md) for the state matrix
and commands.
