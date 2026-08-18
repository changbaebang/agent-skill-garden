---
name: critical-review
description: >-
  Reviews a diff for high-confidence release-blocking regressions only, including
  data loss, crashes, authorization bypass, exploitable security issues, infinite
  loops, and broken critical flows. Use for critical review, release blocker,
  심각도 확인, 치명적인 버그만, or 배포 막을 문제. Ignore style and low-impact
  nits. Review is read-only unless publication is separately requested.
---

# Critical review

Inspect the actual base-to-head diff and relevant working-tree changes. Trace each
candidate through caller, changed code, side effect, and affected user or system.

Report a finding only when all of these are present:

1. a concrete trigger;
2. a reproducible or strongly evidenced failure path;
3. meaningful release impact;
4. evidence that the regression comes from the reviewed change;
5. a specific remediation direction.

Do not inflate uncertainty into a blocker. Investigate plausible critical paths;
if evidence remains incomplete, report residual risk rather than a finding.

For each finding include severity, file and line, trigger, failure, impact,
evidence, and fix direction. If none qualify, say that no release-blocking
regression was found and list any unverified critical path.

Use [references/severity.md](references/severity.md) for the inclusion gate.
