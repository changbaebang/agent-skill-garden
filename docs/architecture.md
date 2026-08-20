# Architecture

## Goal

Maintain one public-safe workflow definition that can be discovered by both
Claude Code and Codex without maintaining two divergent copies.

```text
historical private workflows
          |
          | deliberate promotion, not automatic copying
          v
core/skills + core/policies
          |
          +-- adapters/cursor --> .agents/skills + .cursor/rules
          |
          +-- adapters/claude --> .claude/skills
          |
          +-- adapters/codex  --> .agents/skills
          |
          +-- integrations + local profile --> environment-specific facts
          |
          +-- evals + local evidence --> keep / tune / merge / retire
```

## Canonical layer

`core/skills` follows the common Agent Skills shape: a directory containing a
required `SKILL.md` and optional scripts, references, assets, and product UI
metadata. Canonical frontmatter uses only `name` and `description`.

`core/policies` contains principles that should remain stable across workflows.
They are kept out of individual skills to avoid repetition.

## Adapter layer

Adapters define discovery paths and always-on guidance. They do not fork skill
bodies. The installer links the same skill directory into Claude Code and the
shared `.agents/skills` root used by Codex and Cursor.

## Environment layer

`integrations` describes reusable service or engine behavior. A local
environment profile supplies actual paths, repositories, branches, URLs,
workspaces, and aliases. The public template keeps every integration disabled,
and the profile never contains credentials or mutation authority.

`scripts/bootstrap.sh` combines one adapter, canonical skill links, and a local
profile on a new machine. It is a conservative initializer, not an automatic
merge or a complete backup of host state.

## Promotion, not synchronization

Private configurations can suggest improvements, but changes enter this repository
through a reviewable promotion:

1. identify the reusable decision or procedure;
2. remove organization-, person-, and tool-specific assumptions conceptually;
3. author the generalized workflow directly in `core`;
4. validate structure and public safety;
5. test discovery and behavior in both adapters.

No script copies a private tree and sanitizes it in place.

## Context and evaluation layer

`scripts/context_report.py` measures deterministic character counts for the
always-visible catalog and on-demand bodies. These are cross-model proxies, not
token claims. `evals/routing.json` keeps synthetic routing and side-effect cases
versioned without publishing real conversations.

Usage evidence is optional and local. It informs maintenance decisions but does
not mutate skills automatically.
