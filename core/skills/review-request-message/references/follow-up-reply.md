# Follow-up reply in the review request thread

After the author has handled review feedback, one short reply in the original
request thread tells the reviewers to look again. The reply must say what
actually happened. The loop that drives the review to a settled outcome,
including re-requesting on the code host, is `review-response-loop`; this
reference only shapes the thread reply.

## Classify before writing

Read the current pull request head, the review submissions, the inline threads,
the author's replies, and the commits made after the feedback. For each
reviewer:

| Class | Meaning |
| --- | --- |
| `answered` | the author replied with reasoning or a decision; no verified code change for that feedback |
| `updated` | a later commit or the current diff proves the requested change was applied |
| `mixed` | some feedback updated, some answered or deferred |
| `pending` | the latest actionable feedback has no author response and no verified resolution |

Mention only reviewers whose feedback is `answered`, `updated`, or `mixed`. Do
not mention every assignee or every participant by default. Say nothing about a
`pending` item; it has not been handled.

## Accuracy rules

- A code change is verified from the head commit, a later commit, or the current
  diff. A reply that says "will fix" is not a change.
- A reasoned "not changing this in this pull request" reply is `answered`, not
  `updated` and not `pending`.
- Never write "all addressed" when any item was deferred or answered without a
  change.
- Leave reviewer-owned unresolved threads unresolved; the reviewer decides after
  reading the response.
- Do not paste the code host discussion into the thread. Summarize only whether
  feedback was answered, updated, or mixed. Add a comment link only when it
  helps the reviewer jump to several dispersed threads; the parent message
  already carries the pull request link.

## Shapes

Keep the whole reply to one or two sentences after the mentions.

Answered only:

```text
{mentions}
I have replied to your comments; please take another look when you can. 🙏
```

Updated only:

```text
{mentions}
I have applied your suggestions and left notes on each thread; please take
another look. 🙏
```

Mixed:

```text
{mentions}
Some comments are applied and the rest answered on the threads; please take
another look. 🙏
```

Where an automated reviewer only wakes on a chat mention with a fixed phrase,
that phrase and the account's identity belong in the environment profile or a
private extension. Put the human reply first and the automation trigger on the
final line of the same message; never use the trigger wording for a human.

## Availability gate

Checking whether a human is away is the user's responsibility, not something
to infer from profile status. Show the human mention candidates and ask the
user to confirm availability once per candidate list; a short answer in context
("neither is away", "only the second one is away") is enough. If the same
request already stated availability for exactly these candidates, do not ask
again. Mention only confirmed-available humans; never swap in a group mention
or another person. Automation accounts need no confirmation. If every human is
unavailable and no automation needs a trigger, send nothing.

## Do not repeat yourself

Read the thread before replying. Do not post a second follow-up for the same
pull request head unless the user explicitly asks for it again.

## Write boundary

Find the parent message by the pull request link and verify it contains that
link before replying. Draft by default; send only when the user says to post,
send, notify, or tell them. Resolving review threads, requesting reviewers on
the code host, and editing code are separate actions the user must ask for.
