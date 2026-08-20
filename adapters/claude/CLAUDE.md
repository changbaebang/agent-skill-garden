# Portable workflow adapter for Claude Code

Use the installed skills before generic exploration for non-trivial work.
Match requests against skill descriptions, including natural-language phrases.
Read-only analysis may start automatically. Do not infer permission for commits,
pushes, messages, deployments, branch changes, or destructive operations.

Keep portable workflow, integration behavior, local environment values, and
private organization policy separate. Verify authorized external writes by
reading the resulting state back. Treat unavailable verification as a
limitation, not a pass.

When a selected skill needs local repositories, publication targets, or service
aliases, resolve one environment profile before inferring those values.

Keep tool-specific invocation syntax out of canonical `SKILL.md` files.
