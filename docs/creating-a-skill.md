# Creating a portable skill

1. Start from a repeated request with a stable procedure or important trap.
2. Choose a short lowercase hyphenated name.
3. Put trigger phrases and exclusions in `description`.
4. Keep `SKILL.md` procedural and below 500 lines.
5. Move detailed templates and evidence rules into `references/`.
6. Put deterministic repeated logic into `scripts/` and test it.
7. Avoid tool names unless the workflow genuinely requires one tool.
8. Run `./scripts/validate.sh`.
9. Install into a temporary project and test explicit plus natural-language use.

A portable skill must not contain private repository names, internal domains,
personal absolute paths, credentials, or instructions that silently authorize
external side effects.
