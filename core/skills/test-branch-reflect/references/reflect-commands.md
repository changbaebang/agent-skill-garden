# Reflecting a work branch onto a shared test branch

Names below stand for values the caller supplies: `$base` is the integration
branch, `$target` the shared test branch, `$work` the work branch, `$remote`
the remote (usually `origin`).

## One command for the whole sequence

```bash
scripts/reflect_branch.sh --target "$target" --work "$work"            # prepare only
scripts/reflect_branch.sh --target "$target" --work "$work" --push     # after approval
scripts/reflect_branch.sh --target "$target" --work "$work" \
  --pick "$sha1" --pick "$sha2" --push                                 # approved commits only
```

`--base` overrides the detected default branch; `--remote` overrides `origin`.
Without `--push` nothing leaves the machine, so the first form is safe to run
before the user has decided. The script exits 1 on any guard, 2 on usage, and
aborts a conflicted merge or pick so the tree is left clean.

## The same steps by hand

Preconditions:

```bash
git fetch --prune "$remote"
git status --porcelain                     # must print nothing
```

Refresh the base without touching the working tree:

```bash
git merge-base --is-ancestor "$base" "$remote/$base" || echo "local base is ahead: stop"
git merge --ff-only "$remote/$base"        # when $base is checked out
git update-ref "refs/heads/$base" "refs/remotes/$remote/$base"   # otherwise
```

Rebuild the test branch, refusing when the local copy has unpushed commits:

```bash
git log --oneline "$remote/$target..$target"   # must print nothing
git checkout -B "$target" "$remote/$target"
```

Merge the remote tip with a merge commit:

```bash
git merge --no-ff "$remote/$work" -m "merge: $remote/$work into $target"
```

On conflict, list the files and abort rather than resolving on a shared branch:

```bash
git diff --name-only --diff-filter=U
git merge --abort
```

Cherry-pick approved commits, recording the origin hash in each message:

```bash
git log --oneline "$remote/$base..$remote/$work"   # candidates, show the user
git cherry-pick -x "$sha1" "$sha2"
```

Push, never with force:

```bash
git push "$remote" "$target:$target"
```

## Merge or cherry-pick

| Situation | Choice | Why |
| --- | --- | --- |
| merge applies cleanly | merge with a merge commit | one revertable unit, hashes preserved |
| whole merge conflicts because the test branch drifted from the base | cherry-pick | moves only the work, not the drift |
| work is one or two commits | cherry-pick | smaller surface, easier to read on the shared branch |
| user wants to test part of the branch | cherry-pick the named commits | explicit approval per hash |

Cherry-picked commits get new hashes. When the work branch is later merged
into the base and the base into the test branch, the same change arrives
twice; git usually resolves the duplicate silently, but a later edit to the
same lines will conflict. The `-x` trailer is what lets someone trace the
duplicate back.

## When the push is rejected

A non-fast-forward rejection means another person pushed to the test branch
between the fetch and the push. Rerun from the fetch; the rebuild step starts
again from the new remote tip and the work is re-applied on top. Do not add
`--force` or `--force-with-lease`: either one discards the other person's
commits.

## Report template

```text
base    : main @ 3f2a1c9
work    : feature/cart-badge @ 8b17d02 (origin tip)
mode    : merge                         # or: cherry-pick 8b17d02 c41e9aa
target  : staging 61d0e77 -> a9c4f30 (pushed)
next    : wait for the test environment deployment, then verify the change there
```

With cherry-pick, add one line: "picked commits carry new hashes; expect
duplicates when the work branch is merged for real".
