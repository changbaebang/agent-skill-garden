# Shared branch sync matrix

## Preconditions

```bash
git fetch --prune origin
git status --porcelain            # must be empty
git rev-parse --abbrev-ref HEAD
```

## Compare

```bash
ahead=$(git rev-list --count "origin/$b".."$b" 2>/dev/null)
behind=$(git rev-list --count "$b".."origin/$b" 2>/dev/null)
```

| State | Action |
| --- | --- |
| `ahead` is 0 | update the branch |
| `ahead` is greater than 0 | stop, report the commits, let the user decide |
| no local branch | `git branch --track "$b" "origin/$b"` |

## Update

```bash
# checked-out branch
git merge --ff-only "origin/$b"

# any other branch, without touching the working tree
git update-ref "refs/heads/$b" "refs/remotes/origin/$b"
```

`git update-ref` is preferred over checkout plus reset because the working tree
is never modified, so unrelated in-progress work is unaffected. `git branch -f`
has the same effect but fails on the checked-out branch, which is why the two
cases are separated.

## Report

```text
main   abc1234 -> def5678   (+12)
stage  already current
qa     skipped: local is 3 commits ahead
         a1b2c3d fix(cart): ...
```

Skipped branches are reported separately from updated ones.
