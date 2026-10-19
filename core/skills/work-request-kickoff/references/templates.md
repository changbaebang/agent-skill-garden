# Templates

Fill every template in the language of the thread. Keep the headings; drop a
section only when the sweep proved it empty, and say so in the section instead
of deleting it silently.

## Work definition

```markdown
## Work definition

### One line
[what, for whom, by when]

### Background
- Anchor: [link]
- Requested by: [who, in which meeting or thread]

### In scope
- [ ] ...

### Out of scope
- ...

### Dates and commitments
- [each commitment with its source]

### Owner candidates
| Candidate | Evidence (source) | Confidence |
| --- | --- | --- |
| @name | ... | high / medium / low |

### Open questions
- ...

### Proposed next actions
- [ ] Send the kickoff reply to the owner (after approval)
- [ ] Fill the tracker item (intake)
- [ ] Split the work (work-triage)
```

## Kickoff reply

```markdown
@owner, hello.

[One or two sentences: what was agreed or requested, where, with the link.]

I have not been able to find [the schedule / the ticket body / the document],
so it is hard to plan the next step from here. I may well have missed where it
lives.

When you have a moment, could you share [a date / a one-line scope / the next
action] for this? A short kickoff is more than enough.

Thank you.
```

Rules the draft must follow:

- fact, then ask, then thanks; nothing about who is late;
- name the missing thing precisely; a vague "any update?" wastes the reply;
- ask for the smallest unblocking item, not for the whole plan;
- link the tracker item when one exists;
- one sentence that leaves room for the requester having missed something.

## Thank-you reply (after the owner answers)

```markdown
@owner, thank you for the details. I will go through [the ticket / the
document] and confirm [the time / the scope] from there.
```

## Preparation output

```markdown
## Preparation

### Documents read
- [ ] Tracker item [key]
- [ ] [document]
- [ ] [repository doc]

### Scope draft
- Modules: ...
- First milestone: ...

### Files and directories to inspect
- `...`

### Risks and dependencies
- ...

### Next step
- intake, when the ticket is still thin
- work-triage, then work-start, when the scope is clear
```
