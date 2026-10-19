# Counting reach

`scripts/blast_radius.mjs` turns "how far does this change go" into numbers.
It makes no judgement; the five questions in `SKILL.md` do.

## Invocation

```bash
node scripts/blast_radius.mjs --diff                 # default branch ... HEAD
node scripts/blast_radius.mjs --diff origin/develop  # named base ... HEAD
node scripts/blast_radius.mjs src/a.tsx src/b.css    # whole files, no diff
node scripts/blast_radius.mjs --diff --all           # every reporting file
node scripts/blast_radius.mjs --diff --json          # machine-readable
node scripts/blast_radius.mjs --root path/to/repo --diff
```

`--diff` and explicit files are exclusive. The script runs from the repository
root it discovers with git, so it works from any subdirectory. When `--diff`
has no base, the base is the remote default branch, then `origin/main`,
`origin/master`, `main`, `master`; if none exists, pass the base explicitly.

Only source files are scanned: `.js`, `.jsx`, `.ts`, `.tsx`, `.mjs`, `.cjs`,
`.css`, `.scss`, `.less`. Test, spec, and story files are neither scanned nor
counted as consumers; a default or selector inside a test reaches nobody.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | nothing flagged (there may still be consumers) |
| 1 | at least one flagged file: an always-on pattern or an override |
| 2 | usage or environment error (not a git repository, unknown base, bad option) |

A non-zero exit is a signal for the caller, not a failure of the counter.

## What is counted

**Consumers.** The exported symbols that appear in the touched lines, or in
the whole file when the touched lines contain no `export` (a style constant
inside an exported object is the usual case). Each symbol is searched as a
whole word across the committed tree; the count is the number of other source
files that reference it, with up to three sample paths. At most twelve symbols
per file are searched, and generic names (`Props`, `Options`, `Config`, `index`
and similar) are skipped because they inflate every number.

The search runs only where reach can leave the owning package: the file is
flagged, its package has at least one dependent workspace package, or the
repository declares no workspaces at all. A file inside one application with no
dependents is not searched; that application's own review sees its consumers,
and the search is the slow step on a large tree.

**Dependent packages.** When the repository declares workspaces
(`pnpm-workspace.yaml` or the root `package.json` `workspaces` field), the
owning package of each changed file is resolved to the nearest `package.json`,
and every workspace package that lists it under `dependencies`,
`devDependencies`, `peerDependencies`, or `optionalDependencies` is named. The
text output prints up to eight names and the remaining count; the JSON output
carries the full list. A repository without workspaces produces no dependent
list; the consumer count still applies.

**Cannot opt out.** A match means the change applies to every consumer, with
no variant, prop, or selector that turns it off:

- `base:` followed by a class-list value (string, template, array, or a
  class-joining call) as in class-variance style variant helpers; an object
  field such as `base: baseUrl` does not match;
- `defaultVariants`, `defaultProps`;
- global selectors: `:root` anywhere, `html` or `body` only when the line opens
  a rule block (`body {`, `html, body {`), so a request `body` variable does
  not match;
- `@layer base`.

Default parameter values (`= false`) are deliberately not matched; they are
too common to be a signal.

**Overrides a value.** A match means a value was overwritten; the reviewer has
to decide whether a cause was removed or an observation was hidden:

- `style.setProperty` (an inline write outranks every stylesheet);
- `!important`;
- `documentElement.style` written directly;
- library-wide `.defaults` assignment;
- `Object.assign` onto `window`, `globalThis`, or `document`.

Both lists are plain arrays at the top of the script. Add a pattern when a
repository has its own "applies to everyone" or "overwrites" idiom; keep the
reason string short, because it is printed under the flag.

## Reading the numbers

- Counts are **upper bounds**. A short or common symbol name matches comments
  and unrelated identifiers. Open the sample paths before quoting a number.
- The default output shows **flagged files only**. A large diff can touch
  shared exports in dozens of files; listing all of them hides the two lines
  that matter. `--all` prints everything. With no flags, the three widest
  consumer lists are printed for orientation.
- Consumers are read from the committed tree (`HEAD`), so uncommitted edits to
  consumer files are not seen. Commit before counting when that matters.
- A keyword counted as a symbol makes the number meaningless. The export
  pattern matches `const enum` before `const` for that reason; if a new
  keyword form appears in a repository, extend the pattern rather than
  accepting a four-hundred-file "consumer" count.

## JSON shape

```json
{
  "base": "main",
  "files_scanned": 3,
  "flagged_count": 1,
  "consumer_only_count": 1,
  "shown": ["packages/ui/src/button.tsx"],
  "results": [
    {
      "file": "packages/ui/src/button.tsx",
      "package": "@fixture/ui",
      "dependents": ["admin", "web"],
      "always_on": ["`base:` style of a variant helper; a variant cannot switch it off"],
      "overrides": [],
      "consumers": [{ "name": "buttonStyles", "count": 3, "sample": ["apps/web/src/home.tsx"] }],
      "flagged": true
    }
  ]
}
```

`results` holds every reporting file; `shown` is the subset the text output
would print under the same options.
