# Verdicts and evidence

The commands use the GitHub CLI. On another host, keep the questions and swap
the commands: which run belongs to the head commit, what the step log says,
whether the step may fail without failing the pipeline, and how the pattern is
distributed across branches.

## Find the run for the head commit

```bash
pr=<number>
repo=$(gh repo view --json nameWithOwner --jq .nameWithOwner)
sha=$(gh pr view "$pr" --json headRefOid --jq .headRefOid)

gh run list --repo "$repo" --commit "$sha" \
  --json databaseId,name,conclusion,headBranch \
  --jq '.[] | [.databaseId, .name, .conclusion] | @tsv'
```

Pick the row whose name is the gate workflow. Two rows with the same name for
one commit means the gate ran twice; keep that fact for the report. The
`conclusion` column is the check color and proves nothing on its own.

## Read the step log

```bash
run=<databaseId>
gh run view "$run" --repo "$repo" --log > gate.log
python3 scripts/gate_log_triage.py classify --log gate.log
```

The first output line is the verdict. Each following line is a kind, a line
number, and the log text:

| Kind | Meaning |
| --- | --- |
| `passed` | a line stating the gate passed |
| `failed` | a line stating the gate failed |
| `incomplete` | a timeout or "analysis not finished" line |
| `condition` | a threshold comparison printed under a failed verdict |

Verdict rules: an `incomplete` line without a `passed` line is `no-verdict`,
even when the step also printed an error; a `failed` line without a `passed`
line is `failed`; `passed` beside `failed` or `incomplete` is `conflicting`;
nothing matched is `unknown`. Both of the last two mean a person reads the log.

Quote the line number and text in the report and in any comment. "The log says
so" is not evidence; the line is.

### When the tool words its verdict differently

Pass a JSON object with any of the groups `passed`, `failed`, `incomplete`,
`condition`; each group you give replaces the default list for that group only:

```json
{
  "passed": ["gate verdict: GREEN"],
  "incomplete": ["result not available after \\d+ seconds"]
}
```

```bash
python3 scripts/gate_log_triage.py classify --log gate.log --patterns patterns.json
```

## Is the step allowed to fail?

```bash
grep -rnE 'continue-on-error|allow_failure|\|\| true' .github/workflows .gitlab-ci.yml 2>/dev/null
```

Read the hit in context: the setting must sit on the gate step, not on an
unrelated one. Then check whether the base branch requires the check at all:

```bash
base=$(gh pr view "$pr" --json baseRefName --jq .baseRefName)
gh api "repos/$repo/branches/$base/protection/required_status_checks" \
  --jq '.contexts[]' 2>/dev/null
```

An empty list, or a list without the gate check, means a gate failure does not
block the merge. Record the file and line of whichever setting applies.

## Tally the pattern across branches

```bash
workflow="<gate workflow name as the run list prints it>"
gh run list --repo "$repo" --workflow "$workflow" --limit 8 \
  --json databaseId,headBranch,headSha \
  --jq '.[] | [.databaseId, .headBranch, .headSha] | @tsv' |
while IFS=$'\t' read -r run branch commit; do
  verdict=$(gh run view "$run" --repo "$repo" --log 2>/dev/null \
    | python3 scripts/gate_log_triage.py classify \
    | awk -F'\t' 'NR == 1 { print $2 }')
  printf '%s\t%s\t%s\t%s\n' "$run" "$branch" "$commit" "$verdict"
done > runs.tsv

python3 scripts/gate_log_triage.py tally --runs runs.tsv \
  --branch "$(gh pr view "$pr" --json headRefName --jq .headRefName)"
```

| `reading` | Meaning | Path |
| --- | --- | --- |
| `repo-wide` | two or more branches have no-verdict runs | infrastructure; communicate |
| `branch-local` | only the triaged branch has them | this change made the analysis heavier; treat as a real failure |
| `single-branch` | one other branch has them | inconclusive; widen the window with a larger `--limit` |
| `none` | every run produced a verdict | the timeout was a one-off; say so |

`duplicate_commits` counts commits that ran more than once. Report it as a
possible contributor, never as the confirmed cause.

## Dashboard link

Build it from the log when the tool prints one, otherwise from the gate's base
URL in the environment profile. When neither is available, write that the link
is unknown rather than guessing a host. When the dashboard sits behind a
private network, say so next to the link so a reader outside it does not read a
connection error as a missing result.
