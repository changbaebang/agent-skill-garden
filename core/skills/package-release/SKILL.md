---
name: package-release
description: >-
  Releases a personal package: picks the version from the unreleased changelog,
  moves Unreleased to a version header, replaces version literals, proves the
  tarball and CLI, and opens the release pull request. Use for release this
  package, cut a release, bump to 1.2.0, 0.5 or 0.4.1?, 릴리스 PR 만들어줘,
  패키지 릴리즈. The user tags and publishes. Not for app deploys, test
  branches, blog posts, or a release already shipped.
---

# Package release

A release changes a contract, so every step below produces evidence for a
decision the user makes: which version, what the changelog promises, whether
the artifact that leaves the machine matches. The agent prepares and proves;
the user tags, and the tag triggers publication.

| This skill does | It does not |
| --- | --- |
| argue for a version from the changelog | push the tag; a protected tag rule reserves that for the user |
| promote the changelog header and sweep version literals | publish to the registry; the release workflow does that from the tag |
| prove the tarball and the CLI before anything is pushed | deploy an application or reflect onto a test branch |
| open the release pull request, and merge only when told | announce the release |

## Start from the remote, not the checkout

The main checkout is almost always behind: the user merges and tags on the
host, so only the remote moves. Fetch, read the manifest version from the
remote default branch, and compare it with the local one. When they differ,
the local number is the stale one, and bumping from it recreates a version
that already shipped. Do the work in a fresh worktree on the remote default
branch.

## Decide the version from the contract, not the number

1. Does the Unreleased section contain a breaking change: a raised runtime
   requirement, a removed public export, a changed CLI flag, exit code, or
   output shape? On 0.x that is a minor; from 1.0 it is a major.
2. Otherwise additions are a minor and fixes alone are a patch.
3. On 0.x a caret range pins to the minor, so a minor may carry breaking
   changes. "When 1.0?" is therefore not a version question but a surface
   freeze: does the README state what is stable, and is there evidence that
   surface holds without a major? Decline 1.0 while no release has ever
   carried a breaking change or no consumer has run the package for real.
   Soak time is measured in downstream CI cycles, not weeks on a calendar.

`scripts/release_prep.py suggest` reads the Unreleased section and proposes a
level with its reason. It is evidence; the decision stays with the user.

## Find every version literal by searching, not from memory

The number of places a version is written differs per repository and changes
between releases, so a remembered list always misses one. Run
`scripts/release_prep.py scan` from the new worktree and change what it finds:

- the manifest version;
- `## [Unreleased]` becomes `## [X.Y.Z] - YYYY-MM-DD`: the header is replaced,
  not followed by a new section, so no entry is duplicated;
  `scripts/release_prep.py changelog --version X.Y.Z` does this and retargets
  the compare link, as a dry run until `--write`;
- example output in the README, generated snapshots, and every other hit;
- a preamble in the future tense ("the next release will") is rewritten in
  the present.

A test that asserts the version as a literal breaks on the next bump too;
derive it from the manifest instead. When Unreleased was left empty by several
preparation pull requests, filling it is part of this release: deferring was
right then, because parallel edits to the same lines conflict, and the release
pull request is where that debt is paid.

## Gate with `&&` only

Install dependencies first in the new worktree; without that the build fails,
or the pack produces a tarball with no build output. Then chain build,
type-check, tests, lint, a pack dry run, and the CLI's version flag with `&&`
and nothing else. Read the pack listing and confirm the build output directory
is in it. When the CLI writes files that embed the version, such as generated
workflow or config files, generate one and confirm it carries the new version.

A `;` or `||` anywhere in the chain is a hole: one real run had a failed build
swallowed by a push fallback, and a worktree holding no release commit was
pushed as the release branch. Commands are in
[references/release-commands.md](references/release-commands.md).

## Open the release pull request

The default branch requires a pull request. One commit titled
`chore: release X.Y.Z` is enough. The body states what changed, grouped as in
the changelog; why this version, naming the breaking change when there is one;
the gate's measurements, such as tarball file count, test count, and the
version flag's output; and the exact tag commands for the user to copy. Use
[references/release-pr-template.md](references/release-pr-template.md).

Merging is the user's call. Merge only on an explicit instruction for this
pull request, and then with a squash and branch deletion so the history shows
one release commit.

## After the tag, observe only

The tag push starts the release workflow, which authenticates with the
registry's trusted-publisher identity instead of a stored token. Check the
workflow run's conclusion, the registry's latest version, and the release
object. Do not re-run a failed workflow after editing it: a re-run uses the
workflow as it was at the tagged commit, so the user must recreate the tag.
Known failure modes and their fixes are in
[references/traps.md](references/traps.md).

## Boundaries

- Never create or push a tag, even when the rules would allow it today.
- Never edit the repository's registry configuration to get around a
  corporate mirror; point the one-off lockfile refresh at the public registry
  on the command line instead.
- Confirm which account the host CLI will use before opening the pull request
  on a personal repository; a work identity on a personal release is a mistake
  that outlives the release.
- A sentence that only reports a release ("shipped 0.3.0") is not a request;
  ask what, if anything, should happen next.
