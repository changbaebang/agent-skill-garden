# Evolution across three agents

This repository is the public result of actual use across Cursor, Claude Code,
and Codex. It is not a claim that every host behaved identically or was active
at the same time.

## Experience timeline

### Cursor

The first generation used editor rules and request-triggered workflows. It
established the value of capturing repeated review, planning, and verification
procedures, but tool-owned formats made reuse and synchronization difficult.

### Claude Code

The next generation moved procedural workflows into Agent Skills and separated
always-on guidance from dynamically loaded instructions. This made progressive
disclosure and explicit skill invocation practical.

### Codex

The current generation added skill-first routing rules, local session evidence,
strict read-versus-write boundaries, and read-back verification after authorized
changes. It also made cross-host drift visible instead of assuming identical
files meant identical behavior.

## Current support boundary

| Host | Repository role | Current verification claim |
| --- | --- | --- |
| Cursor | Historical source and supported skill path/rule adapter | Structure and installation path verified against current documentation |
| Claude Code | Active personal environment | Install and workflow smoke target |
| Codex | Active personal environment | Install, local audit, and workflow smoke target |

Cursor currently supports `.agents/skills` as a project and user skill root, so
the shared installation path is intentionally reused for Cursor and Codex. See
the current [Cursor Agent Skills documentation](https://cursor.com/docs/skills).
The repository does not create a duplicate `.cursor/skills` tree.

## Lessons retained in the public design

- Keep the workflow core independent from product syntax.
- Put always-on behavior in small host adapters.
- Treat descriptions as routing interfaces and bodies as on-demand procedures.
- Do not equate installation with invocation.
- Separate skill selection from permission to mutate external state.
- Verify the resulting state after an authorized write.
- Promote reusable ideas into public source instead of sanitizing private trees.
