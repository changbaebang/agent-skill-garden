---
name: private-skill-scaffold
description: >-
  Scaffolds a private, non-published skill under an opaque random directory exposed through an alias symlink. Use for create a private skill, personal skill, sensitive skill, anonymized skill path, 비공개 스킬 만들기, 개인 스킬, 해시 경로 스킬. Not for promoting a skill to a public tree or editing an existing shared skill.
---

# Private skill scaffold

A private skill keeps procedure that must never reach a synced or published
tree. The trick is separation: the real files live in a private root under a
meaningless name, and only an alias symlink appears where the host discovers
skills. The name of the real directory must reveal nothing.

## Decide first

1. Is the content really private? If the reusable decision can be separated from
   the sensitive facts, the reusable part belongs in a shareable skill and only
   the facts belong here or in the environment profile. Split before scaffolding.
2. Does the user want a private skill, or a profile value? A path, account, or
   alias is a profile value, not a skill.
3. Do you have both roots? The private root (outside every synced tree) and the
   host skills root come from the environment profile or the user. Never guess
   them and never default to a location inside a repository.

## Procedure

1. Confirm the alias with the user. It is the only name visible in the shared
   tree, so it must not itself leak the subject. Normalization lowercases and
   reduces it to letters, digits, and hyphens.
2. Run `scripts/private_skill_init.py <alias> --private-root <dir> --skills-root <dir>`
   (or set the two roots in the environment). It creates a random 32-hex
   directory with a minimal `SKILL.md`, then the alias symlink.
3. The script refuses when the alias path is a real directory or already points
   at a private skill. Do not work around a refusal by deleting or overwriting;
   report it and let the user choose a different alias.
4. Verify the link resolves under the private root and that `SKILL.md` exists.
5. Replace the placeholder description with real triggers and an explicit
   not-for exclusion. Keep frontmatter to `name` and `description`; add
   host-specific keys (for example, disabling automatic invocation) only if the
   host needs them and the user wants them.
6. Check the sync boundary before any backup or publish step. See
   [references/sync-boundary-check.md](references/sync-boundary-check.md).

## Traps

- The alias symlink is itself a tracked-looking path. A sync tool that follows
  symlinks copies the private content into the shared tree. Confirm the sync
  excludes links that resolve into the private root.
- A hash directory protects the name, not the content. If the body names the
  subject, tools that index file contents still expose it.
- Do not echo private content into logs, commits, or chat summaries while
  scaffolding. Report only alias, link, and verification result.
- Never commit, push, or publish as part of scaffolding. That is a separate
  authorized step.

## Report

State the alias, whether the link verified, and the sync-boundary result. Do
not print the private root contents.
