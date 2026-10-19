# Release commands

The worked example is a Node package published from a tag-triggered workflow.
Other ecosystems keep the same shape: read the version from the remote, scan
for literals, chain the gate with `&&`, prove the artifact, hand the tag to the
user. Swap the build and pack commands for the ecosystem's own.

## Is the checkout stale?

```bash
cd "$REPO"
git fetch origin --quiet
default=$(git symbolic-ref --short refs/remotes/origin/HEAD | sed 's#^origin/##')
git log --oneline -1 "origin/$default"
node -p "require('./package.json').version"                      # local, do not trust
git show "origin/$default:package.json" | node -pe 'JSON.parse(require("fs").readFileSync(0,"utf8")).version'
```

When the two versions differ, the remote one is current. Start a worktree from
it and do all release work there:

```bash
git worktree add "../$(basename "$REPO")-release" "origin/$default"
cd "../$(basename "$REPO")-release"
git switch -c "release/X.Y.Z"
```

## Propose the version, then decide

```bash
python3 scripts/release_prep.py suggest --changelog CHANGELOG.md
```

The output names the subsections found, the proposed level, and the 0.x
caveat. Read the entries before accepting the proposal; a "Changed" entry that
alters an exit code is breaking even though the subsection name is not.

## Find every literal

```bash
python3 scripts/release_prep.py scan --root .
# or, by hand:
OLD=$(node -p "require('./package.json').version")
grep -rn --exclude-dir=node_modules --exclude-dir=.git --exclude=CHANGELOG.md "$OLD" . | grep -v -- '-lock'
```

The scan skips lock files, the changelog, dependency and build directories,
and binaries, and matches the version as a whole token, so `0.4.0` does not
report `10.4.0`.

## Promote the changelog header

```bash
python3 scripts/release_prep.py changelog --version X.Y.Z             # dry run, prints the diff
python3 scripts/release_prep.py changelog --version X.Y.Z --write
```

The script refuses when there is no Unreleased section, when it is empty, or
when a header for that version already exists. It replaces the header in place
and retargets the `[Unreleased]: ...compare/vOLD...HEAD` link to
`[X.Y.Z]: ...compare/vOLD...vX.Y.Z`.

## The gate

```bash
pnpm install --frozen-lockfile \
  && pnpm build && pnpm typecheck && CI=1 pnpm test && pnpm lint \
  && PACK=$(npm pack --dry-run 2>&1) \
  && echo "$PACK" | grep -q 'dist/' \
  && echo "$PACK" | grep -E 'npm notice (version|total files)' \
  && node dist/cli.js --version
```

Keep the chain exactly this shape: install first, `&&` between every command,
no `;`, no `||`, no fallback on the push line. Record from the output:

- the `total files` count and the `version` the pack reported;
- the test count;
- the `--version` output of the built CLI.

When the CLI generates files that embed the version, run that generator into a
temporary directory and `grep` the new version in the result before moving on.

For a Python package the analogue is `python -m build && tar tzf dist/*.tar.gz`
and running the installed console script with `--version`; for a Rust crate,
`cargo package --list` and `cargo run -- --version`.

## Pull request

```bash
git add -A && git commit -m "chore: release X.Y.Z"
git push -u origin "release/X.Y.Z"
gh pr create --title "chore: release X.Y.Z" --body-file release-body.md
```

When `gh pr edit` fails on a deprecated project-card field, patch the body
through the API instead:

```bash
gh api -X PATCH "repos/$OWNER/$REPO_NAME/pulls/$NUMBER" -F body=@release-body.md
```

Merge only when the user says so for this pull request:

```bash
gh pr merge "$NUMBER" --squash --delete-branch
```

## Tag commands to hand over

Put these in the pull request body verbatim; the user runs them after merging.

```bash
git -C "$REPO" pull && git -C "$REPO" tag vX.Y.Z && git -C "$REPO" push origin vX.Y.Z
```

## After the tag

```bash
gh run list --workflow=release.yml --limit 1 --json conclusion,headBranch --jq '.[0]'
npm view "$PACKAGE" version dist-tags.latest
gh release view vX.Y.Z --json tagName,isDraft,publishedAt
```

Observe and report; do not re-run, re-tag, or publish by hand.
