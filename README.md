# Agent Skill Garden

[English](README.md) | [한국어](README.ko.md)

> A field-tested skill garden shaped by real workflows across Cursor, Claude
> Code, and Codex.

This repository shows how one developer turns repeated engineering work into a
small set of reusable Agent Skills, keeps shared behavior portable, and tests
the operating boundaries around those skills.

It is an opinionated reference setup, not a new agent framework and not a dump
of private configuration. Clone it as a starting point, keep what fits your
work, and cultivate it from evidence in your own usage.

The garden is also a way to carry experience forward. Tools, repositories,
teams, and roles can change, while a well-extracted decision rule or verified
workflow remains useful. Private context stays behind; the reusable judgment,
procedure, and safety boundary travel with the developer.

## The idea

You already repeat useful ways of working with an agent, often without naming
them. This garden helps make those patterns visible:

```text
real work
  -> find repeated requests and decisions
  -> extract a reusable workflow
  -> validate and install it
  -> observe local usage evidence
  -> understand focus-work signals
  -> keep, tune, merge, or prune
```

The audit does not judge productivity or track time. It shows which kinds of
work recur, which skills have local invocation evidence, and which repeated
requests may deserve a new or better skill.

## What you can copy

- Twenty portable workflows for intake, execution, review, verification,
  repository lifecycle, knowledge work, closeout, and skill maintenance.
- Shared policies for skill-first routing, explicit change authority, and
  read-back verification.
- Cursor, Claude Code, and Codex adapters backed by the same canonical skills.
- A non-destructive installer that previews changes and never overwrites an
  existing skill.
- Public-safety, structure, context-budget, unit, and synthetic-eval checks.
- A local-only usage audit that emits aggregates, not prompt text.
- A promotion process that authors public-safe knowledge at the source instead
  of sanitizing a private repository after the fact.

The review workflows use a routed model: `pull-request-review` inspects the
change first, always applies the release-blocker gate, and selects React,
TypeScript, Next.js, hygiene, and side-effect passes only when the diff provides
their signals. Re-review compares heads and verifies fixes instead of producing
new comments from unchanged code. See
[`docs/review-workflow.md`](docs/review-workflow.md).

## Why this is a portfolio project

The repository demonstrates engineering judgment rather than prompt volume:

- extracting stable procedures from repeated real work;
- separating portable policy from host-specific integration;
- designing safe boundaries for GitHub, trackers, messaging, and deployment;
- treating verification as evidence rather than an assertion;
- measuring context growth without inventing token-saving percentages;
- preserving privacy while publishing a reproducible reference setup.

The workflows grew through actual use across Cursor, Claude Code, and Codex.
Claude Code and Codex are the current active environments; Cursor remains part
of the experience history and supported adapter design. See
[`docs/evolution.md`](docs/evolution.md) for the exact support boundary.

## Repository map

```text
core/
  policies/       tool-neutral operating rules
  skills/         canonical Agent Skills
adapters/
  cursor/         Cursor rule and discovery guidance
  claude/         Claude Code discovery guidance
  codex/          Codex discovery guidance
evals/            synthetic routing and safety cases
scripts/          installation, audit, and validation commands
tests/            privacy and event-parser tests
docs/             architecture, adoption, privacy, and project decisions
```

## Quick start in a disposable project

Requirements: Bash, Python 3.9+, Git, and ripgrep (`rg`).

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden
./scripts/validate.sh

mkdir -p work/demo-project
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project

# Review the dry run, then apply it.
./scripts/install.sh \
  --target all \
  --scope project \
  --root work/demo-project \
  --apply
```

Project installation links canonical skills into:

| Target | Project path | User path |
| --- | --- | --- |
| Claude Code | `.claude/skills` | `~/.claude/skills` |
| Codex | `.agents/skills` | `~/.agents/skills` |
| Cursor | `.agents/skills` | `~/.agents/skills` |

Cursor and Codex intentionally share `.agents/skills`. Cursor's current
[Agent Skills documentation](https://cursor.com/docs/skills) lists this as a
discovery path, so the installer does not create a duplicate `.cursor/skills`
tree. Existing destinations are reported as conflicts and left untouched.

The installer links skills only. Review and merge the optional host guidance
under `adapters/` yourself; it never overwrites `CLAUDE.md`, `AGENTS.md`, or
Cursor rules.

Read the full [adoption guide](docs/adoption.md) before installing into an
existing user configuration.

## Discover your repeated work locally

Claude Code and Codex users can audit a recent window without exporting raw
prompts:

```bash
python3 core/skills/skill-usage-audit/scripts/audit_usage.py --days 7
```

Use the output as questions:

- Do the top categories match the work you believe you focus on?
- Does repeated work have skill evidence?
- Are skills selected before unrelated tool exploration?
- Should a repeated low-evidence category become a skill?
- Should a skill with no evidence be tuned, merged, or retired?

`No evidence` is not proof that a skill was never used. Host logs differ, and
the Codex parser infers evidence from explicit invocation or `SKILL.md` reads.
The report is a maintenance aid, not employee monitoring, time tracking, or a
productivity score. See [`docs/audit-and-privacy.md`](docs/audit-and-privacy.md).

## Measure before claiming token savings

Agent hosts and models tokenize text differently. This repository tracks
stable, controllable inputs instead: catalog metadata and on-demand skill-body
size.

```bash
python3 scripts/context_report.py
```

Use provider-reported session usage or a controlled before/after evaluation for
actual token counts. The useful target is lower context cost per successfully
completed task, not merely the shortest prompt.

## Evaluate without publishing private logs

`evals/routing.json` contains synthetic requests with expected skills and
forbidden side effects. Static validation, unit tests, synthetic cases, and
local aggregate evidence form the default feedback loop. Inspect a bounded,
redacted prompt sample only when a specific routing failure cannot otherwise be
explained.

## Initialize a portable blog workflow

`blog-writing-workflow` can inspect an existing Markdown blog, create a local
inventory without copying article bodies, and help the agent produce a
reviewable voice and publication profile. The same profile then guides drafting,
polishing, publication checks, and explicitly authorized publishing.

```bash
python3 core/skills/blog-writing-workflow/scripts/blog_inventory.py \
  path/to/blog \
  --output path/to/blog/.agent-blog/blog-inventory.json
```

The generated inventory and profile stay local by default. The public skill
contains the workflow contract, not one author's content, site URL, or voice.
After installation, users can simply ask the agent to initialize the current
blog, write a draft, run a publication check, or publish an approved post. See
the [blog workflow guide](docs/blog-workflow.md) for the complete onboarding
flow.

## Design rules

- Author public-safe content at the source; do not publish by search-and-replace.
- Keep shared `SKILL.md` files portable and host behavior in adapters.
- Prefer concise metadata and load detailed references only when needed.
- Separate analysis, drafting, local mutation, and external mutation.
- Treat unavailable verification as a limitation, not a pass.
- Add a skill only for repeated work with a stable procedure or important trap.
- Tune, merge, or retire skills when evidence no longer justifies them.

## Scope

This repository is not a marketplace, universal observability platform,
private-config mirror, or guarantee that metadata alone will make every host
select the right skill. It is a cloneable reference for cultivating your own
small, evidence-informed workflow library.

See [`docs/positioning-and-name.md`](docs/positioning-and-name.md) for related
projects and the naming decision.

## License

MIT
