# Environment bootstrap

[English](environment-bootstrap.md) | [한국어](environment-bootstrap.ko.md)

This repository can rebuild the portable workflow layer of a personal agent
environment without publishing one person's machine or organization settings.

## What it restores

For Codex, the bootstrap prepares:

- `~/.codex/AGENTS.md`: portable skill-first and safety guidance;
- `~/.agents/skills`: links to the canonical skills in this clone;
- `~/.agent-garden/profile.ini`: local paths and enabled integrations.

The clone must remain at a stable path because installed skills are symbolic
links. Pulling future repository updates updates those linked skill bodies.

## What it does not restore

The public bootstrap does not copy or generate:

- credentials, tokens, cookies, SSH keys, or connector sessions;
- `~/.codex/config.toml` or provider-specific authentication;
- conversation history or telemetry;
- company-only procedures, repository names, URLs, channels, or aliases;
- permission to commit, push, publish, message, deploy, or mutate a tracker.

Those values either belong to the host, stay local, or live in a deliberately
private repository owned by the user.

## First installation

```bash
git clone https://github.com/changbaebang/agent-skill-garden.git
cd agent-skill-garden

./scripts/bootstrap.sh --target codex
./scripts/bootstrap.sh --target codex --apply
```

Dry run is the default. Application stops before mutation when an existing
guidance file or conflicting skill is detected.

Edit `~/.agent-garden/profile.ini` after installation. All integrations are
disabled in the public template. Enable only what is available in the new
environment, then run:

```bash
python3 core/skills/environment-profile/scripts/profile_doctor.py
```

Restart Codex and test one read-only request for each enabled integration before
authorizing any external write.

## Private backup option

The local profile can be backed up in a private personal repository. Point
`AGENT_GARDEN_PROFILE` at that file after cloning the private repository, or
copy its reviewed values into the default user profile. Confirm that the remote
is private before tracking the file, and never store credentials in it.

```bash
AGENT_GARDEN_PROFILE="$HOME/path/to/private-profile.ini" \
  ./scripts/bootstrap.sh --target codex --apply
```

## Adding another skill

Every new skill should be split across four destinations when necessary:

| Kind | Destination |
| --- | --- |
| Reusable decision, procedure, or safety rule | `core` |
| Reusable service or engine behavior | `integrations` |
| Actual path, repository, branch, URL, workspace, or alias | local profile |
| Organization-only procedure or vocabulary | private extension |

This classification is part of `workflow-maintenance`. A skill is not portable
when a future user must edit its `SKILL.md` merely to replace one person's path
or service identifier.

## Existing environments

Do not use bootstrap as a merge tool. When it reports a conflict, compare the
existing file with the public adapter and merge deliberately. The command never
backs up or replaces the existing file on the user's behalf.
