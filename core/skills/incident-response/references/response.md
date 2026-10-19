# Respond

## Context checklist

Fill every line from what was actually read. Mark anything else unknown.

- Incident key and channel (from `scripts/incident_ref.py`).
- Channel topic: open, mitigating, or resolved.
- Timeline so far: detected, declared, each action, recovery if any.
- Impact: journey, customers, revenue or support signals.
- Roles: who is commander, communications lead, operations lead.
- Open actions and owners.
- Similar past incidents and one lesson from each.
- Proposed time of the next update.

## Roles

| Role | Also called | Owns |
| --- | --- | --- |
| Commander | incident lead | goal, priorities, the single decision point, update cadence |
| Communications lead | announcer | confirmed facts to the announcement channel and stakeholders |
| Operations lead | recovery owner | the fastest recovery path: rollback, hotfix, resources, configuration |

When responders are many and roles are not stated, the channel fills with
parallel investigation and nobody owns the decision. Post the roles explicitly;
asking "who owns this incident?" and acknowledging is itself a first action.

## Ten-minute cards

| Role | Do now | Do not |
| --- | --- | --- |
| Commander | state the goal (stop customer impact), order the actions, fix the update cadence (15-30 minutes) | get absorbed in cause debate |
| Communications lead | post impact, status, next update time to the announcement channel | publish anything unconfirmed |
| Operations lead | execute rollback, workaround, or resource change; share verification evidence | spend time on long reports |

## Fifteen-minute loop

1. Commander restates the goal, the top action, and the next update time.
2. Operations lead reports execution and verification: error rate, sample
   requests, logs.
3. Communications lead publishes only what step 2 confirmed.
4. Repeat with the same format every time the state changes.

## Status update template (incident channel)

```markdown
## [HH:MM] Status — {OPEN | MITIGATING | RESOLVED}

**Impact**: (customers, revenue, journey, one line)
**Symptom**:
**In progress**:
**Next update**: +15 to 30 minutes, or on recovery
**Owners**: @recovery / @commander
```

## Role message templates

```markdown
[Commander]
- Goal: {stop customer impact}
- Priority: {recovery action 1} > {action 2}
- Next update: {HH:MM}

[Communications lead]
- Status: {OPEN | MITIGATING | RESOLVED}
- Impact: {one line}
- Action: {one line}
- Next: {HH:MM}

[Operations lead]
- Executing: {rollback | hotfix | configuration change}
- Verification: {metric, log, or sample request}
- Remaining risk: {one line}
```

## Situation analysis template

```markdown
## {incident key} situation analysis

### Summary
{one line}

### Timeline ({declared time zone})
| Time | Event |
| --- | --- |
| | detected / declared / action / ... |

### Impact
- **Journey or feature**:
- **Customers, revenue, support**:
- **Severity estimate**: (one line of reasoning)

### Current state
- **Channel topic**: OPEN / RESOLVED
- **In progress**:
- **Blockers**:

### Similar past incidents
- {key}: {one-line lesson}

### Proposed next actions (ordered)
1.
2.

### Status update draft (incident channel)
{template above}

### Announcement draft (only if needed before resolution)
{short; the resolution template lives in closure.md}
```

## Signal to first action

| Signal | Suspect | First action |
| --- | --- | --- |
| Right after a deployment or pre-release | configuration or API fan-out | roll back; remove the newly added field or call |
| Database CPU or slow queries climbing | N+1 or chained calls | inspect the call graph of the latest deployment; roll back |
| 5xx on one API | recent deployment or a dependency | roll back; open the circuit |
| Support contacts or failed-payment reports rising | order or payment path | announce; size the impact |
| Message or reprocessing backlog | downstream transfer failure | count affected items; plan the reprocessing |
| One client flow fails, others fine | hard-coded path or deep link mismatch | check the mapping; bypass the entry point |
| Data missing after a batch run | stale static files or cache | regenerate; purge the cache per the runbook |
| Partial refund, discount, or reward mismatches | duplicated calculation logic | enumerate affected records; publish the manual correction basis |

## Repeated patterns and their follow-ups

- **Client path mismatch**: move hard-coded URLs and deep links to a central
  mapping; before deleting an API, confirm no client still calls it.
- **Fan-out and database load**: replace per-item calls with a bulk endpoint or
  cache; add connection and autoscaling limits to the pre-release checklist.
- **Batch, static files, cache**: put the exact regeneration command and purge
  target in the runbook; trace why detection was late.
- **Monetary consistency**: unify duplicated branches of the calculation; add
  the protective condition to the review checklist.
- **Many responders, no roles**: name the roles in the channel topic at
  declaration and record decision, announcement, and recovery bottlenecks
  separately in the postmortem.

## Past-incident search

Search the tracker's incident project for the same service name, the same
error signature, the phrase that marks explicit roles, the phrase used for
prevention actions, and the status that marks follow-ups still in progress.
Carry one lesson per match into the analysis.
