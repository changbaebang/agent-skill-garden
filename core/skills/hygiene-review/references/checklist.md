# Pull-request hygiene checklist

## Dependencies and lockfiles

- Every new import resolves from the correct workspace package.
- Added dependencies are used and classified correctly as runtime, development,
  peer, or optional dependencies.
- Manifest and lockfile changes agree with the package-manager policy.
- Lockfile churn is attributable to the intended manifest change.

## Public surface and repository boundaries

- Barrel files, package exports, and entry points do not expose internal symbols
  accidentally.
- New imports respect documented package and layer direction.
- Generated output, build products, local configuration, and credentials are not
  committed contrary to repository policy.

## Duplication, dead additions, and residue

- New files and exported symbols have a reachable consumer or an explicit
  registration mechanism.
- Constants, types, and utilities do not introduce a second source of truth for
  the same evolving concept.
- Console logging, debugger statements, broad ignores, temporary flags, and
  untracked cleanup markers are absent from production paths.
- Tests and fixtures do not leak into runtime bundles or exports.

## Scope discipline

- Mechanical formatting or generated churn does not obscure functional changes.
- Unrelated dependency or refactor changes are split when they materially impair
  review, rollback, or ownership.
- Documentation changes match behavior when build, test, configuration, or public
  API usage changed.
