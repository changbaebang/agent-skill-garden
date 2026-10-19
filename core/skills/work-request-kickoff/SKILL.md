---
name: work-request-kickoff
description: >-
  Reads a chat work request and the threads around it, defines the work, finds
  the owner by evidence, drafts the kickoff reply, then prepares implementation
  after the answer. Use for kick off this request, who owns this, 업무 요청 왔어,
  담당자 찾아줘, 답 왔어, 문서 읽고 준비. Not for pull request reviews or filing
  tickets. Drafts only; sends nothing.
---

# Work request kickoff

A request that arrives as a chat link carries less than it seems: a name, a
promise made in a meeting, a tracker key whose ticket is empty. Reading only the
linked message is how a kickoff goes wrong. The schedule was agreed two threads
earlier, and the person mentioned is not the one who committed. Collect first,
define second, ask third, and send nothing until told to.

## Find the phase

| Situation | Phase |
| --- | --- |
| A request link or pasted thread; the ask has not been answered | kickoff |
| "They replied" plus the same thread | follow-up |
| The tracker item or the linked documents now have content | prepare |
| The thread asks for a review of a pull request and nothing else | stop: a review request is not work to kick off; point to [pull-request-review](../pull-request-review/SKILL.md) |

## Kickoff

1. **Normalize the reference.** Run
   `python3 scripts/extract_refs.py "<link or pasted text>"`. It returns the
   channel and message identifiers, tracker keys, pull-request links, other
   links, and mentions, and performs no lookup.
2. **Read the whole anchor thread**, the one the link points at, root and every
   reply. Record the requester,
   everyone mentioned, each commitment with its date, the work's name, and every
   link. A date given in a reply overrides the one in the root.
3. **Widen before concluding.** Search the chat for the work's keywords and the
   tracker key, read the anchor channel around the message, and open each linked
   tracker item, document, and repository doc read-only. Stop when two or three
   related threads, the tracker item if one exists, and an owner candidate are
   clear. If still unclear, ask the user one question, not several. See
   [references/context-sweep.md](references/context-sweep.md).
4. **Define the work** with the template in
   [references/templates.md](references/templates.md): one line, background
   with the link, in and out of scope, dates and commitments, owner candidates
   with evidence, open questions. An empty tracker item is a finding. Write
   "ticket body empty"; do not fill it from imagination.
5. **Identify the owner by evidence**, in this order: the person who committed in
   the thread to a schedule, deliverable, or hand-off; the tracker assignee or
   the implementer named in the thread; the person named as owner of the goal or
   feature. Narrow to two candidates at most and confirm with one sentence when
   they tie. Never choose by seniority or by who spoke last.
6. **Draft the kickoff reply.** Short fact, then the ask, then thanks. Name what
   is missing (a schedule, the ticket body, a document), say why it blocks
   planning, and ask for the smallest thing that unblocks: a date, a scope line,
   a next action. Add one sentence that leaves room for having missed something.
   No blame, no pressure. With several owners, either one message mentioning
   all of them or one per role; the user chooses. Write in the thread's language.
7. **Hold the message.** Show the definition and the draft together. Send only
   when the user says to send, and only to the channel they named, the anchor
   channel, or the default alias in the environment profile's chat section. When
   the anchor channel belongs to another team, confirm before posting there.
   After sending, return the message link.

## Follow-up

Re-read the thread from the root; do not patch the definition from memory.
Extract what changed: a moved date, a tracker or document update, a meeting
invite, a different owner. Update the definition and mark each change as new.
Offer a short thank-you reply for the thread; it is a send and needs the same
authorization as the kickoff message. When the reply points at a calendar
invite, read the calendar only through a tool the environment provides. Never
turn "this afternoon" into a time.

## Prepare

Run this once the tracker item or the documents have content, and before any
code change.

1. Read in order: links in the tracker description, then repository docs the
   item or the thread names, then the READMEs of tools the work depends on.
2. Rewrite in-scope from the documents: which modules, which removals, which
   first milestone.
3. Scan the codebase read-only for the named components and for traces of
   earlier attempts; list the affected modules.
4. Produce the preparation output from the templates: documents read, scope
   draft, files to inspect, risks, next step.
5. Hand off. A still-thin ticket goes to [intake](../intake/SKILL.md); a clear
   scope goes to [work-triage](../work-triage/SKILL.md) and then
   [work-start](../work-start/SKILL.md). Do not edit code, create a branch, or
   commit here.

## Do not

- Send a chat message, create or edit a tracker item, or change code without an
  instruction that names that action.
- Review the pull request found in a thread; redirect instead.
- Paste credentials, tokens, or account details into any draft.
- Report a date, an owner, or a ticket state you did not read.
