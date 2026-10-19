# Resolve and postmortem

## Resolution announcement (announcement channel)

Draft it when the channel topic marks recovery or the responders agree on it.

```markdown
## [RESOLVED] {incident key}: {title}

- **Window**: detected {HH:MM} to recovered {HH:MM} ({declared time zone})
- **Impact**:
- **Cause (one line)**:
- **Action taken**:
- **Remaining**: (monitoring, reprocessing count, manual corrections)
- **Channel**: {incident channel}
```

## Follow-up classification

| Item | Rule |
| --- | --- |
| Horizon | short term (within two weeks), medium term (within a month), long term (beyond a month) |
| Shape | action, owner, deadline, verification metric |
| Tracking | weekly review of records in the follow-up-in-progress status |
| Done when | the change is applied, the recurrence detector reads normal, and the runbook or document is updated |

An action without an owner is unassigned. An action without a deadline is
optional. An action without a metric cannot be shown to have worked.

## Postmortem template

```markdown
# {incident key} postmortem — {title}

## Metadata
| Item | Value |
| --- | --- |
| Severity | |
| Impact level | |
| Detected to recovered ({declared time zone}) | |
| Reporter / commander | |

## Summary (three sentences for leadership)
1. What happened
2. Why, in one line
3. What changes

## Timeline
| Time | Event |
| --- | --- |

## 5 Whys
1. Why:
2. Why:
3. Why:
4. Why:
5. Why: **root cause**

## What went well / what did not
-

## Prevention actions
### Short term (within two weeks)
- [ ]
### Medium term (two weeks to one month)
- [ ]
### Long term (beyond one month)
- [ ]

## Action items
| Action | Owner | Deadline | Tracker record |
| --- | --- | --- | --- |

## Follow-up status
| Horizon | Status | Evidence |
| --- | --- | --- |
| Short term | | |
| Medium term | | |
| Long term | | |
| Blockers | | |

## Appendix
- Channel: {incident channel}
- Tracker: {record link}
```

## Rules for the writer

- Each 5 Whys step cites the channel or the tracker. A step without evidence is
  written as "unverified", never filled from intuition.
- Prevention actions are measurable: a monitor, a test gate, a contract check,
  a call-structure verification, a runbook step.
- Every action carries owner, deadline, and metric.
- Before finishing, list the follow-ups still in progress from earlier
  incidents and check the new ones for duplicates and contradictions.
- The recorder is whoever the team designates; when nobody is, the commander
  and the reporter agree on one. Archive the tracker record only after the
  postmortem is accepted.
- Pasting the postmortem into the tracker or a wiki is a write; present the
  draft and wait for the person to ask.

## Follow-up principles that recur

- Removing or rerouting an API needs a cross-client check (web, mobile,
  backend) before the change ships.
- Prioritize by customer impact, not by which team owns the code.
- Hard-coded connections between systems move to configuration or a central
  mapping.
