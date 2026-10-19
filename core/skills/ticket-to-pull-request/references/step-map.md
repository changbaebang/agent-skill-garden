# Station map and re-entry

Each station names what it consumes, what it produces, and which skill does the
work when one is installed. Re-entry means: find the station from the user's
phrasing, read the current state from disk, tracker, and pull request, then
continue from there.

## Stations

| # | Station | Consumes | Produces | Delegates to |
| --- | --- | --- | --- | --- |
| 1 | Understand | tracker key or URL | item summary, labels, linked material, open questions to the user | none |
| 2 | Branch | confirmed base | feature branch from the remote base, preflight checklist, optional in-progress transition | `work-start` |
| 3 | Contract gate | item, deployed specification, client types | one verdict: implementable, blocked, no-op | `api-contract-check` |
| 4 | Align | stations 1 to 3 | acceptance criteria, proposal with file and line, scope boundary, decisions as choices | none |
| 5 | Implement | agreed approach | code and tests | none |
| 6 | Verify | changed tree, base | CI-equivalent lane results with counts, new-versus-baseline diagnostics | `affected-verification` |
| 7 | Smoke | runnable change | pass, fail, or a recorded skip reason | `browser-e2e-check` |
| 8 | Commit | verified tree, user request | commits in the repository's convention with the untruncated key | none |
| 9 | Pull request | commits, base from station 2 | pushed branch, pull request with a "what remains" section, template and gate check | `pull-request-checklist` |
| 10 | Side effects | diff | divergence table, consumer sweep, optional comment | `side-effect-check` |
| 11 | Review | open pull request | answered findings, re-requested review, settled state | `review-response-loop` |
| 12 | Close | merged or settled pull request | evidence summary, wait-or-finish decision, optional tracker closure | `work-closeout`, then `ticket-lifecycle` for the tracker write |

## Re-entry phrases

| User says | Enter at | Read first |
| --- | --- | --- |
| "work on this ticket", a pasted key or URL | 1 | the tracker item |
| "which base should this go on" | 2 | previous item's pull request, remote branches |
| "is the backend ready", "check the contract" | 3 | deployed specification, client types |
| "how should we approach this" | 4 | stations 1 to 3 output |
| "verify and open the PR" | 6, then 9 | working tree, base |
| "open the PR", "update the PR body" | 9 | commits, confirmed base, existing body |
| "what else can this break" | 10 | diff, callers, string references |
| "handle the reviews", "respond to the review" | 11 | unresolved threads, head commit |
| "close the ticket", "finish when merged" | 12 | pull request state |

## Starting a tracker transition

Moving the item to in-progress is a tracker write. Do it when the user asked to
start the item or hand it over, not because the branch was created. The target
is always the item itself; the parent or epic is never transitioned, commented
on, or edited from this flow (`parent-ticket-guard`). Transition identifiers
depend on the tracker's workflow configuration; when a transition fails, list
the available transitions instead of retrying a remembered id.

## Migration and removal items

Acceptance for "remove X" is measurable. Before changing code, count the
occurrences of the removed symbol under the paths the item names and record the
number. The item is done when the same search returns zero and the verification
gate passes. Search string references as well as imports; mocks, stories,
manifests, and deprecated-path annotations hold symbol names the type checker
never sees.
