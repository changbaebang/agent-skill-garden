# Environment boundary

Before creating or promoting a skill, classify each part as portable workflow,
integration recipe, environment profile value, or private extension. Split mixed
candidates across those boundaries.

- Portable decisions, evidence rules, and safety boundaries belong in `core`.
- Reusable service or publication-engine behavior belongs in `integrations`.
- Actual paths, repositories, branches, URLs, workspaces, and aliases belong in
  a local environment profile.
- Organization-only procedure that cannot be represented as configuration stays
  in a private extension.

Profiles describe available facts and mechanisms. They never contain secrets,
authenticate tools, weaken core safety policy, or authorize external writes.
