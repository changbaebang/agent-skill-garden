# Audit and privacy

## Principle

Use the least sensitive evidence needed for each decision. The default workflow
is local-only and requires no Grafana, hosted telemetry, or raw-log upload.

## Evidence levels

| Level | Question | Evidence | Raw prompts required |
| --- | --- | --- | --- |
| Static | Is the library valid and compact? | Files, metadata, links, sizes | No |
| Synthetic | Does a known request select the intended workflow? | Versioned eval cases | No |
| Usage | Which installed workflows show invocation evidence? | Local event summaries | No |
| Diagnostic | Why did a request route incorrectly? | A small redacted sample | Sometimes |
| Outcome | Did the skill improve completion quality and cost? | Controlled before/after run | No private history required |

Run static and synthetic checks routinely. Inspect real prompts only for a
specific routing failure that cannot be explained by metadata and event order.

## Local usage audit contract

Run the aggregate audit locally:

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py --days 7
```

The implementation reads `~/.claude/projects` and `~/.codex/sessions` by
default. Override those paths with CLI options when testing fixtures or a
non-default host configuration. It classifies prompt text in memory and emits
only category counts and skill evidence.

Internally, a host adapter may normalize an event to a record such as:

```json
{
  "host": "codex",
  "category": "code-review",
  "skill": "side-effect-check",
  "invocation_evidence": "skill-file-read",
  "skill_first": true,
  "write_attempted": false,
  "verification_observed": true
}
```

Do not treat a missing event as proof that a skill was never selected. Hosts
expose different events, and compacted transcripts can create false negatives.

The current Claude parser uses explicit Skill tool events. The current Codex
parser infers evidence from an explicit invocation or a `SKILL.md` read in the
same turn. Both parsers are intentionally conservative and version-dependent.

## Data boundary

- Process source logs locally and stream records instead of copying transcripts.
- Do not commit prompts, responses, absolute personal paths, repository names,
  ticket keys, internal domains, identities, or credentials.
- Keep sample inspection opt-in and bounded.
- Redact before writing a diagnostic artifact.
- Export aggregate counts or synthetic fixtures, not raw sessions.
- Keep external observability integrations optional.
- Keep aggregate output local unless the user deliberately chooses to share it.

## Improvement loop

```text
static checks
  -> synthetic routing cases
  -> local usage summary
  -> bounded diagnosis when needed
  -> keep / tune / merge / retire
  -> rerun synthetic cases
```

This loop is a decision aid. Skill changes remain reviewable human decisions.
