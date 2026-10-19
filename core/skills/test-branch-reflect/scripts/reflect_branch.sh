#!/usr/bin/env bash
# Reflect a work branch onto a shared test branch.
#
# Usage:
#   reflect_branch.sh --target BRANCH --work BRANCH [--base BRANCH]
#                     [--remote NAME] [--pick SHA ...] [--push]
#
# Fetches, refuses on a dirty tree, fast-forwards the base, rebuilds the local
# test branch from the remote (refusing when the local copy holds commits the
# remote lacks), then merges the remote tip of the work branch with a merge
# commit, or cherry-picks the listed commits. Pushes only with --push and never
# forces. Branch names come from the caller; nothing is assumed about them.
set -euo pipefail

usage() {
  cat >&2 <<'USAGE'
usage: reflect_branch.sh --target BRANCH --work BRANCH [--base BRANCH]
                         [--remote NAME] [--pick SHA ...] [--push]

  --target  shared test branch to update (required)
  --work    work branch whose remote tip is reflected (required)
  --base    integration branch to fast-forward first (default: remote HEAD)
  --remote  remote name (default: origin)
  --pick    cherry-pick this commit instead of merging; repeatable
  --push    push the test branch afterwards; without it nothing leaves this machine
USAGE
  exit 2
}

die() {
  echo "error: $*" >&2
  exit 1
}

target=""
work=""
base=""
remote="origin"
push=0
picks=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target) [[ $# -ge 2 ]] || usage; target="$2"; shift 2 ;;
    --work) [[ $# -ge 2 ]] || usage; work="$2"; shift 2 ;;
    --base) [[ $# -ge 2 ]] || usage; base="$2"; shift 2 ;;
    --remote) [[ $# -ge 2 ]] || usage; remote="$2"; shift 2 ;;
    --pick) [[ $# -ge 2 ]] || usage; picks+=("$2"); shift 2 ;;
    --push) push=1; shift ;;
    -h|--help) usage ;;
    *) echo "error: unknown argument: $1" >&2; usage ;;
  esac
done
[[ -n "$target" && -n "$work" ]] || usage

git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git work tree"
[[ -z "$(git status --porcelain)" ]] || die "working tree is not clean; commit or stash by hand first"

echo "==> fetch $remote"
git fetch --prune --quiet "$remote"

if [[ -z "$base" ]]; then
  base="$(git symbolic-ref --quiet --short "refs/remotes/$remote/HEAD" 2>/dev/null || true)"
  base="${base#"$remote/"}"
  [[ -n "$base" ]] || die "cannot detect the base branch from $remote/HEAD; pass --base"
fi

for branch in "$base" "$target" "$work"; do
  git rev-parse --verify --quiet "refs/remotes/$remote/$branch" >/dev/null \
    || die "$remote/$branch does not exist"
done
[[ "$target" != "$base" ]] || die "target and base are the same branch"
[[ "$target" != "$work" ]] || die "target and work are the same branch"

echo "==> base: fast-forward $base to $remote/$base"
current="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo HEAD)"
if git rev-parse --verify --quiet "refs/heads/$base" >/dev/null; then
  if ! git merge-base --is-ancestor "refs/heads/$base" "refs/remotes/$remote/$base"; then
    git log --oneline "$remote/$base..$base" >&2
    die "local $base holds commits missing from $remote/$base; resolve by hand"
  fi
  if [[ "$current" == "$base" ]]; then
    git merge --ff-only --quiet "$remote/$base"
  else
    git update-ref "refs/heads/$base" "refs/remotes/$remote/$base"
  fi
else
  git branch --quiet --track "$base" "$remote/$base"
fi

echo "==> target: rebuild $target from $remote/$target"
if git rev-parse --verify --quiet "refs/heads/$target" >/dev/null; then
  local_only="$(git log --oneline "$remote/$target..$target")"
  if [[ -n "$local_only" ]]; then
    echo "$local_only" >&2
    die "local $target holds commits missing from $remote/$target; push or drop them by hand"
  fi
fi
git checkout --quiet -B "$target" "$remote/$target"
before="$(git rev-parse --short HEAD)"
work_tip="$(git rev-parse --short "$remote/$work")"

conflict_report() {
  git diff --name-only --diff-filter=U >&2
}

if [[ ${#picks[@]} -gt 0 ]]; then
  echo "==> cherry-pick ${#picks[@]} commit(s) from $remote/$work onto $target"
  resolved=()
  for sha in "${picks[@]}"; do
    full="$(git rev-parse --verify --quiet "${sha}^{commit}")" || die "unknown commit: $sha"
    git merge-base --is-ancestor "$full" "refs/remotes/$remote/$work" \
      || die "commit $sha is not on $remote/$work"
    if git merge-base --is-ancestor "$full" HEAD; then
      die "commit $sha is already on $target; nothing to pick"
    fi
    resolved+=("$full")
  done
  if ! git cherry-pick -x "${resolved[@]}"; then
    conflict_report
    git cherry-pick --abort
    die "cherry-pick conflicts in the files above; nothing was pushed"
  fi
  mode="cherry-pick"
  for full in "${resolved[@]}"; do
    mode="$mode $(git rev-parse --short "$full")"
  done
else
  echo "==> merge $remote/$work into $target"
  if ! git merge --no-ff --quiet "$remote/$work" -m "merge: $remote/$work into $target"; then
    conflict_report
    git merge --abort
    die "merge conflicts in the files above; nothing was pushed. offer --pick with user-approved commits"
  fi
  mode="merge"
fi
after="$(git rev-parse --short HEAD)"

if [[ "$push" -eq 1 ]]; then
  echo "==> push $target to $remote"
  if ! git push --quiet "$remote" "$target:$target"; then
    die "push rejected: $remote/$target moved since the fetch. rerun; it rebuilds from the new tip. never force"
  fi
  pushed="pushed"
else
  pushed="not pushed; rerun with --push once the user approves"
fi

cat <<REPORT
done
  base    : $base @ $(git rev-parse --short "$remote/$base")
  work    : $work @ $work_tip ($remote tip)
  mode    : $mode
  target  : $target $before -> $after ($pushed)
REPORT
