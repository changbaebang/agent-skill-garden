# Watching for review activity

A round begins when new review activity appears after a known point in time.
Establishing that point, and re-establishing it every round, is the mechanical
part of the loop.

## What the watch reports

`scripts/review_activity.py` takes review and comment records plus a timestamp
and returns two things:

- **New activity** since that timestamp, excluding the author's own writes.
- **A verdict**: whether the loop is finished, waiting, or holding a new finding.

Keep both. The activity list alone cannot tell a fresh approval apart from a
fresh finding, and the verdict alone hides who acted.

## Re-establishing the timestamp

Build the watch input again each round instead of editing the previous one in
place. A partial edit that silently fails leaves the old timestamp behind, and
the next run re-reports activity that was already handled.

## Narrow the watch while waiting on someone

A watch that stops on any new activity is consumed by an unrelated approval.
When a specific reviewer has been re-requested, filter to that reviewer and use
a short window so silence surfaces as a prompt to ask again rather than as an
indefinite wait.

## Excluding the author

Filter the author's own reviews and comments by resolving the current account at
run time. A hardcoded account is wrong for everyone else who installs the
workflow: their own writes are not filtered, and the account that is filtered
belongs to someone whose findings they need to see.

Another agent may also write under the same account. Such writes are filtered
together with the author's, so check the thread list directly from time to time.

## Reading the data

The two record sets answer different questions and both are needed.

- Review submissions carry state: approved, changes requested, or commented.
- Inline comments carry the file, line, and comment identifier a reply needs.
- Thread resolution state is separate from both, and unresolved threads are the
  only ones this round has to answer.
