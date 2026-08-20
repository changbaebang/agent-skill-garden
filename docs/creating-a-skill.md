# Creating a portable skill

1. Start from a repeated request with a stable procedure or important trap.
2. Classify the candidate into core workflow, integration recipe, environment
   profile values, and private extensions. Split it when more than one applies.
3. Choose a short lowercase hyphenated name for the portable workflow.
4. Put trigger phrases and exclusions in `description`.
5. Keep `SKILL.md` procedural and below 500 lines.
6. Move detailed templates and evidence rules into `references/`.
7. Put deterministic repeated logic into `scripts/` and test it.
8. Avoid tool names unless the workflow genuinely requires one tool.
9. Run `./scripts/validate.sh`.
10. Install into a temporary project and test explicit plus natural-language use.

A portable skill must not contain private repository names, internal domains,
personal absolute paths, credentials, or instructions that silently authorize
external side effects.

Do not turn an environment value into a generic example inside the skill. Public
templates may show synthetic values, while the user's actual profile stays
ignored locally or in a deliberately private personal repository.
