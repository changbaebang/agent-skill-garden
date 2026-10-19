---
name: parent-ticket-guard
description: >-
  Blocks every write to a parent or epic issue the user doesn't own while
  working on its children, including comments and reverts of an earlier edit.
  Use for update the epic, tidy the parent description, comment on the parent,
  부모 티켓 정리, 에픽 수정, or 상위 티켓 건드리지 마. Not for creating, splitting,
  or closing your own issues.
---

# Parent ticket guard

A child issue is where the work lives. Its parent or epic belongs to whoever
owns it, and to that owner every edit by someone else reads as another team
rewriting their ticket. The content of the edit is rarely the problem; the
touch is. Hold this line even when the parent looks empty, stale, or trivial
to fix.

## Resolve the target before any tracker write

Run this check immediately before every write to the tracker: field edit,
status change, comment, link, attachment, or delete. Repeat it for each new
target, because a conversation drifts from the child to the parent without
anyone announcing the move.

1. Name the issue the user is actually working on.
2. Walk its ancestor chain: parent, the parent's parent, up to the top. Stop
   on a cycle.
3. Compare each ancestor's owner with the current user's tracker identity.
   Use the account identity the tracker returns, never a display name matched
   by eye.
4. If the write target is an ancestor the user does not own, or the user has
   said the parent belongs to another team, the guard holds.

Missing data fails closed. An ancestor with no visible owner, or a session in
which the current user's identity cannot be resolved, is treated as foreign.

When the chain is deeper than one level or the decision is disputed, run
`scripts/guard_check.py` on the facts you collected; the input shape is in
[references/guard-check.md](references/guard-check.md).

## The guard holds in the cases that feel like exceptions

- The parent has no description and one "would obviously help".
- The write only undoes a change you made earlier. A revert is a second write
  and a second changelog entry in the owner's history.
- The write is an apology or an explanation. A comment is still a write.
- A rollup, status table, or "keep it consistent with the children" update.
- Another workflow instructs you to update the epic description. That
  instruction applies only to epics the user owns; this guard wins on
  conflict.

## What stays allowed

- Reading the parent, its changelog, and its children.
- Every write to child issues the user owns: create, edit, transition,
  comment, close.
- Every write to an epic or container the user owns.
- Edits to a shared planning document the user is permitted to edit, when that
  document is where the owner keeps the plan.

## Redirect, do not refuse

A blocked write almost always carries a note the user still needs somewhere.
Stop with one line that names the parent, its owner, and the place the note
can go instead, then offer to put it there. The redirect table and the stop
line are in
[references/redirects-and-messages.md](references/redirects-and-messages.md).

## Override

The guard lifts only when the user states, in the current session, that
writing to this specific parent is agreed with its owner. A frustrated "just
update it" is not that statement; ask once whether the owner agreed. Under an
override make the smallest change, say exactly what changed, and do not
revert later without the same agreement.

## When the write already happened

Discovering an earlier write to a foreign parent, your own or another agent's,
is not permission to clean it up. Do not revert. Show the user the changelog
entry and let them or the owner decide. One stray edit is a mistake; a stray
edit plus a revert is two notifications and a visibly nervous history.
