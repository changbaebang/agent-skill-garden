# Split, investigation hand-off, and close

## Split procedure

1. Slice by outcome. Each leaf has one observable result, one dependency, one
   verification method, and fits within the point cap. The work-triage skill
   produces this slicing; this skill records it.
2. Rewrite the original as a container: prefix its summary with the container
   marker the team recognizes, clear its points, and replace the description
   with the leaf table below.
3. Create each leaf through the create procedure with the full contract. The
   parent is the one the original had, or the original itself when the tracker
   allows a leaf under it.
4. If work had already started, transition the matching leaves to the same
   state so the board does not show the work as unstarted.
5. Read every ticket back. Compare the leaf total with the points the original
   carried and record the difference in the container.

## Container description template

```markdown
## Container (split on YYYY-MM-DD)

| Ticket | Points | Scope |
| --- | --- | --- |
| link to the first leaf | 5 | one outcome |
| link to the second leaf | 3 | one outcome |

**Total: 8 points** (this ticket carried 8 points before the split)
```

## Leaf-only queries

Sprint totals and dashboards must exclude containers, or every split is counted
twice. Build the query from three conditions in the tracker's own language:
restrict to the parent, exclude the container marker from the summary, sort by
due date.

## Investigation to implementation

| Investigation ticket | Implementation leaves |
| --- | --- |
| summary says it is an investigation | one leaf per deliverable unit |
| points stay small even if they were raised during the work | points on the team scale |
| actual effort as measured | estimate as judged |
| findings matrix kept in description or comments | links to the findings, the base branch, the verification plan |
| closes with a comment linking the leaves | same parent or the container |

Never close an investigation ticket with implementation points on it. The
implementation cost belongs on the leaves that deliver it.

## Close checklist

- [ ] ticket read back; parent, points, dates, estimate present
- [ ] actual effort present at the actual step (zero counts, empty does not)
- [ ] done transition found by name for this project, not by a remembered id
- [ ] transition applied; ticket read back in the done state with no field cleared
- [ ] merged change reference and its base branch commented on the ticket
- [ ] container: when all leaves are done, close it and comment the roll-up on a parent you own
- [ ] parent owned by someone else: no write, no comment; the note lives on the leaf or the container

## Pull-request merge to leaf done, in one pass

1. Comment the merged change reference and its base branch on the leaf.
2. Set actual effort as measured.
3. Transition to done, or to the closing state the project uses while review is
   still pending. Read back.
