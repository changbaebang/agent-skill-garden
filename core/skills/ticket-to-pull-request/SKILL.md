---
name: ticket-to-pull-request
description: >-
  Runs one tracker work item through branch, contract gate, implement, verify,
  pull request, review, and close; resumable at any step. Use for work on this
  ticket, open the PR, handle the reviews, 이 티켓 진행하자, PR 올리자, 티켓 닫자, or a
  pasted tracker key or URL. Not for creating or splitting items or reviewing
  others' PRs.
---

# Ticket to pull request

One work item passes through fixed stations: understand, branch, contract gate,
align, implement, verify, smoke, commit, pull request, side effects, review,
close. This skill owns the order, the hand-offs, and the rule that no station
is skipped silently. Where a station has its own skill, this skill decides when
to call it and what to carry forward; it does not restate that skill's method.
A delegate that is not installed does not cancel its station: do the minimum
inline and tell the user which skill was missing.

## Principles that hold at every station

- Do not guess a contract. An unverified field, parameter, or endpoint never
  enters the code behind a cast or a speculative adapter. Stop and verify.
- Keep the item's scope. A refactor or foundation change discovered on the way
  becomes a proposed follow-up item, not part of this change.
- Fill context with the user. Automated lookup misses design files, product
  decisions, and the newest specification. Ask once at the start; when a link
  or thread arrives later, open it at once and revisit any decision it changes.
- Record the basis of each decision: file and line, or the contract text.
- Read the parent or epic item; never write to it. `parent-ticket-guard` holds
  even when another step says to update the epic.
- Write authority is per action. Branch creation, tracker transitions, commits,
  pushes, pull requests, comments, and merges each need the user's request.
  Approving the plan is not approving the writes.

## Re-entry

The user rarely starts at station 1. "Open the PR", "handle the reviews", and
"close the ticket" land mid-flow. Resume from that station using the state on
disk, in the tracker, and in the pull request, never from memory of an earlier
session. The phrase-to-station map is in
[references/step-map.md](references/step-map.md).

## Stations

1. **Understand.** Fetch the item and everything it links. Note labels that mark
   it as depending on a backend change, blocked, or following another release.
   Ask the user for related material (API documentation, product spec, design
   file, recorded decisions) even for pure UI work; pure UI skips the contract
   gate, not this question.

2. **Branch.** Recommend a base, then confirm it as a choice, not in prose: the
   recommended base, the default branch, or one the user names. An item stacked
   on an epic bases on the epic's integration branch; find it from the previous
   item's pull request. Create the branch from the freshly fetched remote base,
   because local heads go stale. The confirmed base is the pull request base
   later; do not re-decide it. Run `work-start` for the preflight. Transition
   the tracker item to in-progress only when the user asked to start it. For a
   migration or removal item, count the remaining occurrences of the removed
   symbol now; acceptance is that count reaching zero.

3. **Contract gate.** When the item depends on a backend change, run
   `api-contract-check` before any code and act on its verdict: implementable
   continues; blocked stops with the exact endpoint, field, and owner to chase;
   no-op ends the item with the evidence and deletes an empty branch. Without
   that skill, read the specification deployed to the target environment,
   trace the route the client actually takes to it, and compare with the
   client's current types yourself. A design document alone is not the contract.

4. **Align.** When the picture is complete, do not start coding. Present the
   requirement as acceptance criteria, the proposed change with file and line,
   the scope boundary (what stays untouched, what becomes a follow-up), and the
   open decisions and risks. Where the approach forks, offer the fork as a
   choice.

5. **Implement.** Follow the repository's architecture and conventions; reuse
   existing patterns, contexts, and flags. Add a test for every new behaviour
   or branch, with its regression case beside it.

6. **Verify.** Run `affected-verification`: it computes the same scope CI
   will, runs every lane, and tells environment traps from real failures. Do
   not rebuild that procedure here, and do not replace it with a hand-picked
   package list; one missed consumer passes locally and fails in CI. Without
   the skill, read the CI definition and run its exact lanes on the affected
   set, judging lint and dependency diagnostics as new-versus-baseline.

7. **Smoke.** If runtime behaviour changed, exercise it in a real browser or
   runtime; type checks and unit tests do not count. Use `browser-e2e-check`
   where available, otherwise drive the page directly. Skipping is allowed only
   for comment, test, or type-only changes, with the reason recorded. A failure
   returns to station 5.

8. **Commit.** Only when asked. Follow the repository's message convention and
   carry the tracker key untruncated. `scripts/work_item_key.py` extracts keys
   whose prefix contains digits, which a naive pattern cuts in half.

9. **Pull request.** Base is the branch confirmed at station 2. The request to
   open it covers pushing the feature branch and nothing else: no merge, no
   push to the base. The body states what remains: follow-ups split out and
   values awaiting confirmation. Run `pull-request-checklist` against the
   repository's template and gates before asking for review. See
   [references/pull-request-body.md](references/pull-request-body.md).

10. **Side effects.** Run `side-effect-check`. First, if a function was
    delegated or replaced, build the return-value divergence table in
    [references/divergence-table.md](references/divergence-table.md); a caller
    search answers who calls, not what changed. Post the result as a pull
    request comment only when the user asks.

11. **Review.** Hand the open pull request to `review-response-loop`. Treat a
    green quality-gate check as unproven when the workflow is configured to
    continue on failure. Apply a fix only after the user has seen the proposal,
    unless the user's wording for that finding was already an instruction.

12. **Close.** Run `work-closeout` for the evidence summary. After a review
    round, ask: keep watching, or finish. Never finish unilaterally, except
    when the user pre-authorized "finish when merged"; then a merge observed
    by the watch ends the watch and reports. Tracker closure and effort fields
    go through `ticket-lifecycle`, on the user's explicit request.

## Do not

- Put an unverified contract into code to keep moving.
- Replace the CI-equivalent verification scope with a shorter list.
- Merge, push to the base, or transition the parent item.
- Resume a station from memory when the repository and pull request can state
  the current position.
