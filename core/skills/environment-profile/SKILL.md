---
name: environment-profile
description: >-
  Initializes, validates, and migrates a local environment profile that maps
  portable skills to actual repositories, draft folders, publication engines,
  messaging workspaces, and available transports. Use for set up my environment,
  move these skills to another computer, configure my blog repository, environment
  doctor, 환경 프로필, 환경 이전, 블로그 경로 설정, or integration setup. Never
  stores credentials or grants mutation authority.
---

# Environment profile

Choose one mode: `initialize`, `doctor`, or `migrate`. The profile records local
facts. It does not replace a skill, contain business procedure, authenticate a
connector, or authorize an external write.

## Resolve one profile

Use the first available source and do not silently merge profiles:

1. an explicit `--profile` path supplied by the user;
2. `AGENT_GARDEN_PROFILE`;
3. `<project>/.agent-garden/profile.ini`;
4. `~/.agent-garden/profile.ini`.

Read [references/profile-contract.md](references/profile-contract.md) before
creating or changing a profile.

## Initialize

For a new user environment, preview and apply the repository bootstrap before
editing individual profile values:

```bash
./scripts/bootstrap.sh --target codex
./scripts/bootstrap.sh --target codex --apply
```

The bootstrap is run from the repository root. It refuses to overwrite existing
host guidance or skills. For profile-only initialization:

1. Ask which repeated skills need environment facts. Inspect only relevant
   local paths and visible tool capabilities.
2. Separate site or service facts from workflow policy. For a blog, repository,
   drafts, engine, branch, and public URL belong here; voice and article
   structure remain in the blog's writing profile.
3. Start from [references/profile.example.ini](references/profile.example.ini),
   remove unused integrations, and show inferred values before writing. Prefer
   the initializer because project scope creates an ignore rule before the
   profile:

   ```bash
   python3 scripts/profile_init.py --scope project --root PROJECT_ROOT
   ```

4. Keep the profile local by default. A user may deliberately keep it in a
   private personal repository and select it with `AGENT_GARDEN_PROFILE`; do not
   publish it with this repository. Never inspect credential files or place
   tokens, passwords, cookies, private keys, or copied conversations in it.
5. Run the doctor and report failures and runtime-only checks separately.

## Doctor

Run:

```bash
python3 scripts/profile_doctor.py --root PROJECT_ROOT
```

Pass `--profile PATH` when the profile is outside the default locations. Static
checks prove profile shape and local paths only. A host connector warning means
the active Claude Code or Codex session must still verify tool visibility and
authentication.

## Migrate

1. Restore the profile from a private backup or create it from the public
   example. Do not copy credentials.
2. Update the small set of machine-specific paths and service aliases.
3. Run the doctor on the destination machine.
4. Open a fresh agent session, test one read-only request per enabled
   integration, and keep external writes explicitly gated.

When another skill needs an integration, load the selected profile and use only
that integration's section. Missing profile data is a configuration gap, not
permission to infer paths, channels, or publication targets.
