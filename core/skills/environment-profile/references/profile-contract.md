# Environment profile contract

The environment profile maps portable workflow names to local facts. Keep
workflow decisions in skills, host discovery in adapters, reusable service
behavior in integration recipes, and organization-only procedure in private
extensions.

## Classification gate

Classify every new personal-skill candidate before implementation:

| Kind | Contains | Destination |
| --- | --- | --- |
| core workflow | reusable decisions, sequence, evidence, safety boundary | `core/skills` or `core/policies` |
| integration recipe | reusable behavior for Slack, Jekyll, GitHub, or another service | `integrations` |
| environment profile | actual local path, repository, branch, URL, workspace, or alias | local `profile.ini` |
| private extension | organization-specific policy or workflow that cannot be expressed as data | private local skill |

A candidate can produce artifacts in more than one kind. Split them instead of
embedding environment values in a public skill or copying portable procedure
into a profile.

## Resolution

Select exactly one profile:

1. explicit `--profile` path;
2. `AGENT_GARDEN_PROFILE` environment variable;
3. project `.agent-garden/profile.ini`;
4. user `~/.agent-garden/profile.ini`.

Profiles are not merged implicitly. Explicit selection prevents a personal
publication target from being combined with a work messaging workspace.

## Required shape

```ini
[profile]
schema_version = 1
name = personal
visibility = local

[integration.blog]
enabled = true
driver = jekyll-git
```

Each enabled `integration.*` section requires a driver. Driver-specific fields
are defined in the corresponding recipe under
[`integrations/`](../../../../integrations/README.md).

The public example keeps all integrations disabled so a fresh bootstrap does
not claim access to repositories or services that were never configured.

Paths support `~` and environment-variable expansion. Relative paths resolve
from the directory containing `profile.ini`.

## Safety

- Never store tokens, passwords, cookies, API keys, private keys, credentials,
  or copied private conversations.
- `visibility = local` is the default. When the profile is inside a Git worktree,
  it must be ignored. The project initializer writes `.agent-garden/.gitignore`
  before creating `profile.ini`.
- `visibility = private-repository` is an explicit declaration that the user
  manages the profile in a separate private repository. The doctor cannot prove
  remote visibility and reports that boundary for manual confirmation.
- `visibility = team` is allowed only for a deliberately reviewed, non-personal
  profile. Prefer committing `profile.example.ini` and keeping each user's
  `profile.ini` ignored.
- A profile can describe an available write mechanism but cannot authorize its
  use. Current-session approval remains required.
- Keep a personal profile untracked or in a private backup. Commit only a
  reviewed team-safe profile with no personal or secret values.
- Profile validation is local evidence. Connector login and service behavior
  still require runtime verification in the active host.
