# Replying and resolving

## Carry the commit

A reviewer may be reading an older head. Every reply that claims a fix names the
commit that made it. Without it the reviewer has to guess whether they are
looking at the current state.

## Keep replies short

State the conclusion. Detail belongs in the commit message and the pull request
body, where it stays discoverable after the thread is resolved.

A reply that refuses a finding carries evidence instead of length: the current
code, the behaviour before the change, or the contract that makes the concern
inapplicable.

## What resolving means

Resolve a thread once it is settled: the fix is in, or the reason not to fix it
has been given.

Leave a thread open when the reviewer asked something only a human can answer
and no human has answered yet. Resolving it removes the signal before anyone
sees it, which is the opposite of what the reviewer asked for.

Leave it open too while an exchange is still live and the reviewer is owed a
reply they have not yet seen.

## Publishing is a separate authorization

Replies, thread resolution, review re-requests, and labels are external writes.
Being able to perform them is not permission to perform them. Confirm the target
before writing, write once, and read the result back.

## After the round

Say what happened in one line when re-requesting review: how many findings were
answered, how many changed code, and the commit. When nothing changed, say that
plainly rather than implying a fix.
