# Measuring what a remote branch deletion loses

## Collect candidates

```bash
me=$(gh api user --jq .login)

gh pr list --author "$me" --state all --limit 300 \
  --json number,state,headRefName \
  --jq '.[] | [.state, .number, .headRefName] | @tsv' > prs.tsv

git fetch --prune origin -q
git ls-remote --heads origin \
  | awk '{sub("refs/heads/","",$2); print $2}' | sort > heads.txt
```

The default branch, for the guard list:

```bash
gh api "repos/$owner/$repo" --jq .default_branch
```

## Do not measure with revision counts or diffs

The same branch, measured three ways:

| Method | Result | Correct? |
| --- | --- | --- |
| `git rev-list --count "$base".."$branch"` | 5972 commits | no, counts commits merged in from the base |
| `git diff --stat "$base" "$branch"` | 6713 files changed | no, counts everything the base did since |
| `git cherry "$base" "$branch"` | 43 commits | yes |

The first two answer "how far apart are these two refs", which is not the
question. The question is "what content would disappear".

## Measure by patch identity

```bash
git cherry "origin/$base" "origin/$b" | grep -c '^+'
```

A `+` marks a commit whose content is absent from the base; a `-` marks one
already contained, including commits that were squashed on merge. Zero means
nothing is lost.

Report it together with:

```bash
git log -1 --format='%ad · %an' --date=short "origin/$b"
```

## Record recovery, then delete

```bash
git ls-remote --heads origin "$b"      # tip revision, record it
git push origin --delete "$b"
```

Write the recorded revisions to a file and give the user the path.

Recovery:

```bash
git push origin "$sha:refs/heads/$b"
```

Some hosts offer a restore control on the closed pull request for a while, but
that is not a durable guarantee. The recorded revisions are.
