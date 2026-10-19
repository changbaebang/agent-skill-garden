# Traps

Every row was hit in a real release. The fix column is the shortest path that
worked, not the only one.

| Trap | Symptom | Fix |
| --- | --- | --- |
| Stale checkout | the bump recreates a version that already shipped | read the version from the remote default branch; work in a fresh worktree |
| No install in the new worktree | build fails, or the pack has no `dist/` | install with the frozen lockfile first; keep the gate one `&&` chain |
| `;` or `\|\|` in the gate | a failure is swallowed and a branch without the release commit is pushed | remove every fallback; a push line must be reachable only after the gate passed |
| Protected tag rule | the agent cannot create `v*` tags | hand the tag commands to the user in the pull request body; do not attempt the push |
| Trusted-publisher permission denied | the workflow's publish step fails with a 403 naming the identity exchange | in the registry's trusted-publisher settings for the package, open the entry's edit form and allow the full publish action; newer entries default to a staged publish only, and the list view does not show the difference |
| Registry URL in the runtime setup action | the same 403 | setting a registry URL there writes an empty auth token into the runtime's config, which blocks the identity exchange; remove the setting |
| Re-running a fixed workflow | the old workflow runs again | a re-run executes the workflow as it was at the tagged commit; the user must delete and recreate the tag |
| Corporate registry mirror cooldown | a just-published version is refused as immature | refresh the lockfile with the public registry passed on the command line; never edit the repository's registry configuration |
| Wrong account | the pull request is authored by a work identity on a personal repository | check which account the host CLI is logged in as; inject the personal credential per command instead of switching the global login |
| Literal assertion in tests | the next bump fails the suite | derive the expected version from the manifest |
| Empty Unreleased section | nothing to promote, or the header is promoted over an empty body | fill the entries first; the script refuses an empty section |
