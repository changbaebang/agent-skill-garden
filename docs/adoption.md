# Adoption guide

[English](adoption.md) | [한국어](adoption.ko.md)

Adopt the garden incrementally. The safe path is to validate a clone, install a
small set into a disposable project, test routing, and only then consider a
user-wide installation.

For a new machine or an empty user environment, use the separate
[environment bootstrap guide](environment-bootstrap.md). Bootstrap prepares a
portable baseline; this guide remains the safer path for merging into an
existing configuration.

## 1. Clone and validate

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden
./scripts/validate.sh
```

Validation checks:

- required Agent Skill structure and relative links;
- synthetic routing case shape;
- local usage-audit parser and privacy behavior;
- context-character budgets;
- public-safety patterns and unresolved placeholders.

Passing validation proves repository invariants. It does not prove that a host
will route every natural-language request correctly.

## 2. Choose the installation target and scope

| Option | Meaning | Destination |
| --- | --- | --- |
| `--target claude` | Claude Code only | `.claude/skills` |
| `--target codex` | Codex only | `.agents/skills` |
| `--target cursor` | Cursor only | `.agents/skills` |
| `--target all` | Claude plus the shared Cursor/Codex root | both roots, once |
| `--scope project` | Only one repository | under `--root` |
| `--scope user` | Every relevant local project | under your home directory |

Cursor and Codex share `.agents/skills` intentionally. The `all` target does not
install that root twice.

## 3. Start with two or three skills

Read the `description` at the top of each `SKILL.md`. Select workflows that
match work you genuinely repeat. A practical first set is:

- `intake` for turning ambiguous requests into a bounded work unit;
- `critical-review` for release-blocking review findings;
- `side-effect-check` for tracing consumers and regression paths.

Use repeatable `--skill` flags to install only that set:

```bash
mkdir -p work/demo-project
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --skill intake \
  --skill critical-review \
  --skill side-effect-check
```

This is a dry run. Read each `PLAN` line and confirm the source and destination.

## 4. Apply without overwriting

Run the same command with `--apply`:

```bash
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --skill intake \
  --skill critical-review \
  --skill side-effect-check \
  --apply
```

The installer creates symbolic links to this clone. Keep the clone at a stable
path. An existing destination is reported as `SKIP` and is never replaced.
Resolve a conflict manually after comparing both skill bodies.

To install all skills, omit every `--skill` flag.

## 5. Merge host guidance deliberately

The installer does not edit always-on configuration. Review one relevant
adapter:

- Claude Code: `adapters/claude/CLAUDE.md`
- Codex: `adapters/codex/AGENTS.md`
- Cursor: `adapters/cursor/rules/agent-skill-garden.mdc`

Merge only non-conflicting ideas into your existing file. The essential
contract is:

1. choose a matching skill before generic exploration;
2. start safe, read-only steps when the request is clear;
3. treat skill selection and permission to mutate as separate decisions;
4. verify authorized writes by reading the resulting state back.

Do not copy private paths, credentials, company rules, or host-specific syntax
into the shared skill bodies.

## 6. Verify discovery and routing

Restart or open a fresh agent session after installation. Test at least three
requests:

1. an obvious positive trigger, such as “review this diff for release blockers”;
2. a natural phrase you use in daily work;
3. a nearby negative case that should not invoke the skill.

Use `evals/routing.json` as synthetic examples. Record:

- expected and observed skill;
- whether the skill was selected before unrelated tools;
- whether forbidden external changes remained untouched;
- what evidence was unavailable.

A symlink proves installation, not runtime discovery. A skill-file read proves
loading, not successful task completion.

## 7. Audit recent local usage

The optional audit currently reads Claude Code and Codex local session formats:

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py --days 7
```

Choose a host or JSON output when useful:

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py \
  --days 30 \
  --host codex \
  --format json
```

The report contains aggregate categories and skill evidence. It does not emit
prompt text. No external Grafana or hosted telemetry is required for this loop.

Interpret the result as signals:

- high-frequency categories suggest actual focus work;
- repeated categories with little skill evidence suggest a create-or-tune
  candidate;
- installed skills with no evidence suggest inspection, not automatic deletion;
- low skill-first counts suggest trigger overlap or late routing.

Categories are keyword-based, not time tracking or productivity measurement.
See `docs/audit-and-privacy.md` before extending the parser.

## 8. Cultivate one change at a time

For a repeated low-evidence workflow:

1. collect a few redacted examples of your real phrasing;
2. decide whether to create a skill or tune an existing description;
3. keep the stable procedure in `SKILL.md` and conditional detail in
   `references/`;
4. add positive and negative synthetic cases;
5. run `./scripts/validate.sh`;
6. repeat the routing smoke test;
7. review the next local audit window.

Do not mutate skills automatically from usage counts. Keep, tune, merge, and
retire decisions reviewable.

## 9. Move to user scope only when stable

Preview first:

```bash
./scripts/install.sh \
  --target all \
  --scope user \
  --skill intake \
  --skill critical-review
```

Then repeat with `--apply`. User scope uses `~/.claude/skills` and
`~/.agents/skills`. Environment overrides `CLAUDE_HOME` and `AGENTS_HOME` are
supported.

Rollback is intentionally manual: remove only the exact symbolic links created
by the installer. Never recursively delete an entire host configuration
directory.

## Platform note

The scripts are validated with Bash and Python on macOS and Ubuntu CI. Native
Windows shells are not currently verified; use WSL or adapt the installer and
contribute a tested path.
