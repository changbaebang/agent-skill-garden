---
name: skill-usage-audit
description: >-
  Audits Claude Code or Codex usage evidence against installed skills to find
  repeated work with no skill, skills loaded late or not at all, weak trigger
  descriptions, overlap, and unused complexity. Use for skill audit, optimize my
  skills, 스킬 최적화, 스킬 사용 점검, 스킬 발동 잘 되나, or AI 사용 패턴 분석.
  Read-only unless the user explicitly requests skill changes.
---

# Skill usage audit

## Inventory first

Run `scripts/inventory.py` to inventory Claude and Codex skill roots. Treat
filesystem presence as discovery evidence, not proof of invocation.

For a privacy-preserving overview, run:

```bash
python3 scripts/audit_usage.py --days 7
```

The script classifies local prompts in memory, reports aggregate work categories
and skill evidence, and does not emit prompt text. Treat its top categories as
focus-work signals, not time tracking or productivity scores.

## Sample real requests

Use a user-specified period or a recent representative window. Inspect actual
request samples, not only counts. Remove tool results, system injections,
subagent prompts, repeated pasted assistant output, and truncated noise.

For Claude Code, an explicit skill invocation event can be direct evidence. For
Codex, loading a `SKILL.md` in the same turn is useful evidence but may still
produce false negatives when logs are compacted or metadata-only routing occurs.
Use “no invocation evidence” rather than “never invoked.”

## Diagnose before changing

Check in order:

1. Did the skill exist and remain discoverable during the sampled period?
2. Does its description contain the user's real phrases and clear exclusions?
3. Do several skills compete for the same request?
4. Did routing happen after generic exploration had already started?
5. Is the request repeated and procedural enough to deserve a skill?

Classify recommendations as create, tune description, merge, retire, or keep.
Attach request samples and confidence. Do not publish private prompts or skill bodies.

Read [references/evidence.md](references/evidence.md) before interpreting logs.
