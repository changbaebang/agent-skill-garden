# Skill-first routing

For a non-trivial request, inspect available skill names and descriptions before
generic exploration. Load the smallest matching workflow, then begin its safe
read-only steps immediately.

Skill selection does not grant mutation authority. A skill may route the work,
but external writes, messages, deployments, commits, pushes, branch changes,
and destructive operations still require the user's intent to cover them.

If a matching skill is discovered after exploration starts, switch to it and
use its contract for the remaining work.
