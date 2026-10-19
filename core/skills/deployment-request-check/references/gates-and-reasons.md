# Gates, reason codes, and edge cases

## Fetch the state, then judge it

Fetch each change as JSON and hand the JSON to the gate script. The example
uses the GitHub CLI because its field names are the ones the script reads;
any host API that exposes the same facts works once the fields are mapped.

```bash
gh pr view 482 --repo OWNER/REPO \
  --json title,url,state,isDraft,mergeable,mergeStateStatus,mergedAt,reviewDecision,statusCheckRollup,author \
  > change-482.json

python3 scripts/pr_gate.py change-482.json --markdown
python3 scripts/pr_gate.py change-482.json --exempt-check "dependency scan"
```

Several changes: write one file per change and combine them into an array
(`jq -s . change-*.json`), or append `{"ref": "OWNER/REPO#N", "error": "HTTP 404"}`
for a change the host refused to return, so it is reported as unverified
rather than dropped.

Use the CLI's own stored login. A stale token exported from a shell profile
produces a forbidden or not-found error that reads like a missing change; unset
the variable and let the CLI resolve its keyring credential.

## Fields the gate reads

| Field | Meaning | Used for |
| --- | --- | --- |
| `state` | `OPEN`, `MERGED`, `CLOSED` | merged passes the review axis; closed holds |
| `mergedAt` | timestamp when merged | treated as merged even when `state` is absent |
| `isDraft` | draft flag | an open draft holds |
| `reviewDecision` | `APPROVED`, `REVIEW_REQUIRED`, `CHANGES_REQUESTED`, or empty | an open change needs `APPROVED` |
| `mergeable` | `MERGEABLE`, `CONFLICTING`, `UNKNOWN` | conflicting holds; unknown is a note to fetch again |
| `mergeStateStatus` | `CLEAN`, `HAS_HOOKS`, `UNSTABLE`, `BEHIND`, `BLOCKED`, `DIRTY`, `UNKNOWN` | dirty holds; behind is a note |
| `statusCheckRollup` | list of check runs (`name`, `status`, `conclusion`, `startedAt`, `completedAt`) and commit statuses (`context`, `state`) | the check axis |

Check outcomes: `SUCCESS`, `NEUTRAL`, `SKIPPED` pass. `FAILURE`, `ERROR`,
`TIMED_OUT`, `CANCELLED`, `STARTUP_FAILURE`, `ACTION_REQUIRED` fail. Anything
still running is pending. An unrecognised completed conclusion is reported as
a failure with its raw value so a person can decide.

## Gate table

| Axis | Merged change | Open change |
| --- | --- | --- |
| Review | passes | `reviewDecision` must be `APPROVED`; draft holds |
| Mergeability | not judged | conflicts hold; behind the base is a note |
| Checks | latest run per name must not fail; pending is a note | latest run per name must not fail and must not be pending |
| Closed without merge | n/a | holds as not mergeable |

Only the latest run per check name counts. A run still in progress is ordered
by its start time, so a fresh re-run supersedes the failure it was started to
replace. A failing latest check on a merged change is still a hold: the merge
did not make the failure pass. If the team accepts it, that is an exemption to
record, not a fact to ignore.

## Exemptions

Some teams run a check that fails routinely and is not a release blocker, such
as an advisory dependency scan or a static-analysis quality gate. Keep the
exact check names in the environment profile, alongside the repository and the
name of the tracker's ready-for-deployment status, so they are not retyped or
guessed. Pass them to the script with `--exempt-check NAME` and copy every line
under `exemptions` in the output into the approval record. A check that is not
on that list is not exempt, however routine its failure looks today.

## Reason codes

| Code | Written on the tracker item | One line for the thread |
| --- | --- | --- |
| `NO_PR` | no change linked; list the sources searched | there is no pull request linked yet |
| `UNVERIFIED` | the host returned an error for the change; include the status | the pull request could not be read |
| `PR_DRAFT` | the change is a draft | the pull request is still a draft |
| `PR_NOT_APPROVED` | `reviewDecision` value and who has reviewed | the pull request still needs approval |
| `PR_NOT_MERGEABLE` | conflict, or closed without merge | the pull request cannot be merged as is |
| `CI_FAILED` | failing latest check names | a required check is failing |
| `CI_PENDING` | running check names | checks are still running |
| `NO_WORK_RECORD` | item has no description, change, or progress comment | the item needs a work record |
| `BLOCKED_ISSUE` | blocking key and its status | KEY is still blocking this |
| `WRONG_STATUS` | current status and why it is not approvable | this item cannot be approved in its current status |
| `NO_READY_TRANSITION` | transitions offered, none is the ready state | the tracker offers no ready-for-deployment transition |

The first seven come from the gate script. The last four come from tracker
context and apply as gates only when a write was requested.

## Edge cases

| Situation | Handling |
| --- | --- |
| Change merged, tracker item not updated | approvable on the change axis; mention the stale item |
| Change open and approved, request made before merge | approvable when the team approves before merging; when unsure, ask in one sentence |
| Several changes, one not approved | hold the whole request; table every change in the record |
| Thread key differs from the change the item links | judge the thread key; state the mismatch in the record |
| Hotfix with a single reviewer | an approval is an approval; headcount is not a criterion |
| Item already in its ready or done state | no transition; reply that it is already there |
| Item cancelled or will not be done | hold with `WRONG_STATUS` |
| Host returns 401 or 404 for a linked change | `UNVERIFIED`, not `NO_PR`; check the credential first |
| Same check name appears twice | the older run is superseded; the script reports how many were ignored |
