# Sync boundary check

Run before any backup, sync, or publish after creating a private skill.

1. Resolve the alias: `readlink <skills-root>/<alias>`. The result must sit
   under the private root. If not, stop and report.
2. Confirm the private root is outside every version-controlled tree, or is
   ignored by it: `git -C <tree> check-ignore <path>` should print the path.
3. Dry-run the sync tool and read the file list. The alias and the random
   directory must both be absent. If the tool follows symlinks, the alias is the
   leak path; exclude it by rule, not by remembering.
4. Search the staged or pending changes for the subject words of the private
   skill. Any hit means the body leaked through another file.
5. Report pass or fail per step. A failure blocks the sync until the user
   decides; do not fix it by editing the sync tool without approval.

Recovery: if private content already reached a shared tree, stop, report the
exact files and revision, and let the user decide on history rewriting. Do not
rewrite history unprompted.
