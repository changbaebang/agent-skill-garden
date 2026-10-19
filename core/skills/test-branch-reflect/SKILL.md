---
name: test-branch-reflect
description: >-
  Reflects a work branch onto a shared QA or staging branch: refresh the base,
  rebuild it from the remote, merge or cherry-pick, push without force. Use for
  reflect onto QA, merge into staging, cherry-pick onto the test branch, qa 반영,
  stage 에 올려줘, 체리픽 해줘. Not for local-only sync, release branches, or
  branch cleanup.
---

# Test branch reflect

A shared test branch is everyone's test bed, not a scratch copy of yours.
Every step below moves history in one direction, from the remote into the
local copy and from the work branch onto the test branch, and nothing is
ever rewritten.

## Name three branches before touching anything

- **Target**: the shared test branch the user named, such as the QA or
  staging branch. When the request does not say which, ask. Pushing to the
  wrong one breaks somebody else's test run.
- **Base**: the integration branch the test branch is meant to track. Default
  to the remote's default branch unless the repository names another.
- **Work**: the branch being reflected, read from its **remote** tip. The
  local copy may hold commits reviewers never saw, or lack commits they did.

Release and deployment branches are not targets for this skill. Decline and
point to the release procedure, even when the request calls one "the test
branch".

## Preconditions

Fetch with pruning. Stop on a dirty working tree and let the user choose
between committing and stashing; never stash on their behalf, because a stash
can revert paths outside the intended set and restore only part of them.
Confirm the remote has all three branches.

## Refresh the base

Fast-forward the local base to the remote. A refusal means the local base
holds commits the remote does not; stop and report them instead of resetting.
When the base is not checked out, move the reference directly so the working
tree stays untouched.

## Rebuild the test branch from the remote

The local test branch is a disposable copy. Before replacing it, compare it
with the remote: when it holds commits the remote lacks, stop and list them,
because replacing it would leave the reflog as their only copy. Otherwise
rebuild it from the remote tip so the reflection starts from what is actually
deployed, not from whatever this machine last saw.

## Merge, or cherry-pick

Merge the remote tip of the work branch with a merge commit, never a
fast-forward, so the reflection is one visible unit that can be reverted as
one.

A conflict means stop: abort, push nothing, report the conflicting files, and
offer the cherry-pick path. Do not resolve conflicts on a shared branch by
guesswork.

Cherry-pick instead of merging when the test branch has drifted so far from
the base that the whole merge conflicts, or when the work is one or two
commits. List the commits the work branch adds over the base, show them, and
move only the ones the user approves by hash. Never choose silently. Record
each picked hash with its origin, because the copies carry new hashes and
will appear as duplicates when the work branch is merged for real; say so in
the report.

## Push without force

Push the test branch only when the user asked for the reflection to reach the
remote; a request to "prepare" or "see if it merges" stops before the push.
Never force-push a shared branch, even when asked: confirm once more and
explain that force discards whatever others pushed since. When the push is
rejected because the remote moved, fetch and redo from the rebuild step. The
rejection is the guard working, not an obstacle to override.

## Report

State the base revision, the work tip, the mode (merge, or cherry-pick with
the hash list), the test branch before and after, whether it was pushed, and
the next step: trigger or wait for the test environment deployment and
verify there. Repeat the duplicate-hash caveat whenever cherry-pick was used.

## Do not

- merge the work branch into the base; this workflow updates the test branch
  only;
- touch release or deployment branches;
- stash, reset, or force anything.

`scripts/reflect_branch.sh` runs the deterministic part, refuses on every
guard above, and pushes only with `--push`. Commands, the merge-versus-pick
decision table, and the report template are in
[references/reflect-commands.md](references/reflect-commands.md).
