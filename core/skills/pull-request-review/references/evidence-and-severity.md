# Evidence and severity

## Evidence gate

A finding needs:

1. the changed behavior or assumption;
2. a concrete trigger or input;
3. the affected runtime path or consumer;
4. the resulting user, data, security, operational, or maintenance impact;
5. evidence that the current change introduced the problem;
6. a minimal remediation direction.

Search repository code, callers, wrappers, types, tests, and history before
claiming that a contract is unsupported. Not finding support is not proof that
support does not exist. When an external contract remains unknown, ask a bounded
question and state what was checked.

Do not flag:

- naming, formatting, or personal style without an explicit rule and impact;
- a generic best practice with no failure path in this change;
- speculative performance advice without cost evidence;
- missing tests without an identified regression or unprotected invariant;
- pre-existing behavior unchanged by the pull request;
- a refactor preference that does not improve an evidenced risk.

## Levels

### Blocker

Use only for a reachable release-stopping defect: data loss, deterministic crash,
auth bypass, exploitable security failure, non-terminating work, or a critical
flow that becomes unusable without a safe fallback.

### Warning

Use for a concrete but non-catastrophic bug, regression, contract mismatch,
reliability failure, or measurable performance problem. State the scenario and
scope accurately; do not inflate it into a blocker.

### Question

Use when code alone cannot determine a policy, external contract, rollout order,
or safety-sensitive intent. Include the checked evidence and the exact missing
fact. A question should not disguise an unsupported accusation.

Questions that cannot change safety or correctness do not belong in the formal
review findings.

## Comment shape

Keep each finding discrete:

```text
Problem: one sentence
Trigger: concrete input or runtime condition
Impact: observable failure and affected scope
Evidence: caller, contract, test, or runtime observation
Fix: minimal direction, not an unrelated redesign
```

Comment on the code, never the author. Be direct and courteous. A calm tone must
not weaken severity, and strong wording must not replace evidence.
