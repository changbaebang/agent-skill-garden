# Local branch safety classes

## Enumerate

```bash
git for-each-ref \
  --format='%(refname:short)|%(committerdate:short)|%(authoremail)|%(upstream:short)|%(upstream:track)' \
  refs/heads
```

Cutoff date, one month back:

```bash
cutoff=$(date -v-1m +%F)          # BSD and macOS
cutoff=$(date -d '1 month ago' +%F)   # GNU
```

## Classify

| Class | Test | Action |
| --- | --- | --- |
| tracked and contained | upstream exists and `git rev-list --count "$upstream".."$branch"` is 0 | candidate |
| merged | no upstream and `git rev-list --count "$base".."$branch"` is 0 | candidate |
| unique work | neither test holds | report the commit count, never delete |

An upstream reported as `gone` does not belong to the tracked class. The remote
copy no longer exists, so treat the branch as unique work and count its commits.

`git branch --merged` alone is unreliable for branches stacked on a base other
than the integration branch. It answers a different question than the two tests
above.

## Delete

```bash
git branch -d "$branch"
```

This form refuses unmerged branches and is the last line of defence. A refusal
means the classification was wrong. Do not reach for the force variant.

## After

```bash
git fetch --prune origin
```

## Recovery

A branch deleted this way stays reachable through the reflog until it expires,
ninety days by default.

```bash
git reflog | grep "$branch"
git branch "$branch" "$sha"
```

## Scale report

Report shape for a repository with hundreds of branches:

```text
total 568 · current branch excluded
  within cutoff (kept)    57
  1-3 months             142
  3-6 months             100
  over 6 months          269

excluded by guard:  other authors 225 · protected names 6
candidates:                          N
unique work, untouched:              N
```
