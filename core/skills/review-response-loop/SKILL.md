---
name: review-response-loop
description: >-
  Drives an already-opened pull request from first review to a settled outcome.
  Watches for new review activity, judges each finding, replies with the fix
  commit, resolves the thread, re-requests review, and re-arms the watch. Use
  for handle the reviews on my PR, keep responding until approval, 리뷰 대응,
  승인까지, 리뷰 다시 요청. Never merges.
---

# Review response loop

Answering a review once is easy. The loop is what breaks: a reply is written,
nobody is asked to look again, and the pull request stalls. This workflow keeps
the cycle alive until the review state settles.

Read-only until a finding is accepted. Applying a fix, replying, resolving a
thread, and re-requesting review are separate authorized actions.

## Establish state first

Derive everything from the pull request itself, not from memory of an earlier
round.

- Repository, number, state, head commit.
- `reviewDecision` and the current requested reviewers.
- Unresolved review threads and their root comment identifiers.
- The reviewer whose response this round is waiting on, if any.
- The initial request and re-request timestamps that bound the review rounds.

`scripts/review_activity.py` turns that data into new-activity and verdict
lines. See [references/watching.md](references/watching.md).

## One round, four closing steps

A round is not finished until all four are done. Dropping either of the last two
is the most common way the loop dies.

1. **Reply** to every finding: the fix commit for accepted ones, the evidence for
   refused ones.
2. **Resolve** the threads that are settled.
3. **Re-request** review.
4. **Re-arm** the watch.

### Re-request even when nothing changed

Reviewers cannot tell that a reply exists. Re-request after a round that only
added reasoning, and say so plainly. A silent watch is not a request.

Prefer the platform's own re-request. Where a reviewer only wakes on a chat
mention, that mention is an integration detail and belongs in the environment
profile, not in this workflow.

If a re-requested reviewer stays silent past a short deadline, request once more.
After a second silence, report it: the reviewer may be unavailable or an
automation may be down.

## Read the findings before answering

Classify the incoming round first. The response differs.

| Signal | Reading |
| --- | --- |
| Same `path:line` raised again in a **later** round | Round-trip |
| A point closed by agreement is reopened | Round-trip |
| The same topic arrives in the **opposite** direction | Round-trip |
| Several reviewers hit one place in the **same** round | Convergence |

Round-trip means the point-by-point answers are not landing. Convergence means
that place is genuinely weak. Both get the same treatment: stop answering
thread by thread, publish one comment covering the whole topic, and point the
threads at it.

Counting `path:line` frequency alone cannot separate the two. Compare authors
inside explicit rounds bounded by request timestamps. See
[references/round-trips.md](references/round-trips.md).

## Judge each finding

Read the file as it stands now. Do not judge from the diff alone or from the
reviewer's summary.

- Accept when the change is real, and prove it after fixing.
- Refuse with evidence: the current code, the behaviour before the change, or
  the contract that makes the concern inapplicable.
- Deferring to a later change is not a resolution while the current head still
  carries the impact.
- A request outside this change's scope gets a boundary, not a fix. Name where
  it belongs.

A question a reviewer raised for human judgement stays open until a human
answers it. Closing it alone removes the signal before anyone sees it.

## Verify before replying

A fix that compiles is not a verified fix. Follow the repository's verification
policy, and prefer checks that exercise the changed behaviour.

Confirm a new test fails without the fix. A test that passes either way proves
nothing and will be trusted later.

## Reply with the commit

Reviewers may still be reading an older head. Every reply that claims a fix
carries its commit. Replies stay short; the reasoning belongs in the commit
message or the pull request body.

See [references/replies.md](references/replies.md).

## Decide whether the loop is finished

An approval is necessary but not sufficient. A reviewer who is not on the
requested list can hold an open comment while the decision already reads as
approved, so the decision alone cannot tell you whether the person you asked has
answered.

| Observed | Reading |
| --- | --- |
| Approved, no unresolved threads, nobody awaited | Finished |
| Approved, no unresolved threads, a re-requested reviewer has not answered | Not finished |
| Any unresolved thread or new finding | Not finished |
| Only approvals arrived while threads remain | Not finished |

While waiting on a specific reviewer, watch that reviewer alone. A watch that
reacts to any activity is consumed by an unrelated approval and stops before the
answer arrives.

## When rounds keep coming

Count the rounds.

| Round | Response |
| --- | --- |
| 1-2 | Judge and answer each finding |
| 3 or more | Publish a self-audit of the whole affected family first |
| A reopened point | Return the behaviour to its previous shape so the question disappears |
| 5 or more without a settled outcome | Report to the user and hand over the decision |

A self-audit sweeps the same family without being asked: every caller of a
changed function, sibling files with the same role, and indirect consumers whose
behaviour changed without being edited. Publish the result even when it is
empty; a stated zero shortens the next round.

Returning a behaviour to its previous shape ends a reopened debate that no
amount of argument can settle, because the policy in question no longer exists
in the change. Widening it may still be correct, but on evidence and separately.

When handing over after repeated rounds, report the round count, how many
findings were real defects, whether the remainder can be decided from code at
all, and the options.

## Do not

- Merge. Approval does not transfer that decision.
- Reply without reading the file the finding points at.
- Close a thread the reviewer opened for human judgement without a human answer.
- Reformat whole directories while fixing one file.
