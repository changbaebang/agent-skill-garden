#!/usr/bin/env node
/**
 * Blast radius: how far a change actually reaches, as numbers.
 *
 * Review time scales with the size of a diff. A one-line edit to a shared base
 * style, a default variant, or a global selector is one line in the diff and
 * every consumer in production. This script turns that mismatch into counts so
 * a reviewer is taken to the right place. It makes no judgement.
 *
 * Three things are counted per changed source file, from the committed tree:
 *   1. reach     - files that reference an exported symbol the change touched,
 *                  and workspace packages that depend on the owning package;
 *   2. always-on - patterns a consumer cannot switch off (base styles, default
 *                  variants, default props, global selectors);
 *   3. override  - patterns that overwrite a value instead of removing a cause
 *                  (inline property writes, !important, global defaults).
 *
 * Usage:
 *   node blast_radius.mjs --diff [BASE]      changed files between BASE and HEAD
 *                                            (BASE defaults to the remote default
 *                                            branch, then main, then master)
 *   node blast_radius.mjs FILE...            whole files, no diff
 *   options: --all   show every reporting file, not only flagged ones
 *            --json  machine-readable output
 *            --root  repository path (defaults to the current directory)
 *
 * Exit codes: 0 nothing flagged, 1 at least one flagged file, 2 usage or
 * environment error. Counts are upper bounds: a common symbol name inflates
 * them, so confirm with the sample paths before quoting a number.
 *
 * Workspace packages are discovered from pnpm-workspace.yaml or the root
 * package.json "workspaces" field. Without either, the repository is treated as
 * a single package and no dependent-package list is produced.
 */
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, readdirSync, realpathSync, statSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';

const SOURCE_RE = /\.(?:[cm]?[jt]sx?|css|scss|less)$/;
const TEST_RE = /\.(?:test|spec|stories)\./;
const MAX_SYMBOLS_PER_FILE = 12;
const SAMPLE_SIZE = 3;
const ORIENTATION_SIZE = 3;
const DEPENDENTS_SHOWN = 8;
const WALK_DEPTH = 4;

// `const enum` must be matched before `const`: matching `const` alone makes the
// following `enum` the symbol name, and a keyword counted as a symbol turns the
// whole number into a lie.
const EXPORT_RE =
  /export\s+(?:declare\s+)?(?:const\s+enum|abstract\s+class|async\s+function|function\*?|const|let|var|class|type|interface|enum)\s+([A-Za-z_$][\w$]*)/g;

// Names too common or too generic to count; they inflate every number.
const SKIP_NAME =
  /^(?:Props|Options|Config|Params|Type|Data|Item|List|index|enum|const|let|var|class|type|interface|function|default|async|declare|abstract)$/;

// Patterns a consumer cannot switch off. A match means "applies to every
// consumer". Default parameter values are deliberately excluded: too noisy.
// `base:` is matched only with a class-list value (string, template, array,
// or a class-joining call) so an object field such as `base: baseUrl` does not
// count. `html` and `body` are matched only as selectors that open a rule block.
const ALWAYS_ON = [
  [/(?:^|\W)base\s*:\s*(?:['"`[]|\w+\()/, '`base:` style of a variant helper; a variant cannot switch it off'],
  [/defaultVariants/, '`defaultVariants`; every consumer that does not pass the variant'],
  [/defaultProps/, '`defaultProps`'],
  [/:root|^\s*(?:html|body)\b[^;{}\n]*\{/m, 'global selector (`:root`, `html`, `body`)'],
  [/@layer\s+base/, '`@layer base`'],
];

// Patterns that overwrite a value. Each may remove a cause or merely hide the
// observation; the reviewer has to ask which.
const OVERRIDE = [
  [/\.style\.setProperty\(/, '`style.setProperty`; an inline write outranks every stylesheet'],
  [/!important/, '`!important`'],
  [/documentElement\.style/, '`documentElement.style` written directly'],
  [/\.defaults\b/, 'library-wide `.defaults` assignment'],
  [/Object\.assign\(\s*(?:window|globalThis|document)\b/, '`Object.assign` onto a global object'],
];

function fail(message) {
  console.error(`[blast-radius] ${message}`);
  process.exit(2);
}

function parseArgs(argv) {
  const options = { diff: false, base: null, all: false, json: false, root: process.cwd(), files: [] };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--all') options.all = true;
    else if (arg === '--json') options.json = true;
    else if (arg === '--root') {
      options.root = argv[i + 1] ?? fail('--root needs a path');
      i += 1;
    } else if (arg === '--diff') {
      options.diff = true;
      const next = argv[i + 1];
      if (next !== undefined && !next.startsWith('-')) {
        options.base = next;
        i += 1;
      }
    } else if (arg.startsWith('-')) fail(`unknown option ${arg}`);
    else options.files.push(arg);
  }
  if (options.diff && options.files.length > 0) fail('--diff and explicit files are exclusive');
  if (!options.diff && options.files.length === 0) fail('pass --diff [BASE] or at least one file');
  return options;
}

const options = parseArgs(process.argv.slice(2));

function gitRaw(args, cwd) {
  return execFileSync('git', ['-C', cwd, ...args], {
    encoding: 'utf-8',
    maxBuffer: 64 * 1024 * 1024,
    stdio: ['ignore', 'pipe', 'ignore'],
  });
}

let ROOT;
try {
  ROOT = gitRaw(['rev-parse', '--show-toplevel'], resolve(options.root)).trim();
} catch {
  fail('run inside a git repository (or pass --root)');
}

// Execute git from the repository root. Arguments never pass through a shell:
// the base ref can come from outside (a pull request's base branch name).
function git(args) {
  try {
    return gitRaw(args, ROOT);
  } catch {
    return '';
  }
}

function gitOk(args) {
  try {
    gitRaw(args, ROOT);
    return true;
  } catch {
    return false;
  }
}

function detectBase() {
  const remoteHead = git(['symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD']).trim();
  if (remoteHead) return remoteHead;
  for (const candidate of ['origin/main', 'origin/master', 'main', 'master']) {
    if (gitOk(['rev-parse', '--verify', '-q', `${candidate}^{commit}`])) return candidate;
  }
  return null;
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf-8'));
  } catch {
    return null;
  }
}

function listDirs(dir) {
  try {
    return readdirSync(dir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory() && !entry.name.startsWith('.') && entry.name !== 'node_modules')
      .map((entry) => entry.name);
  } catch {
    return [];
  }
}

function walkDirs(dir, depth) {
  const found = [dir];
  if (depth === 0) return found;
  for (const child of listDirs(dir)) found.push(...walkDirs(join(dir, child), depth - 1));
  return found;
}

function escapeRegExp(text) {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function expandGlob(pattern) {
  const segments = pattern.replace(/\/+$/, '').split('/').filter(Boolean);
  let dirs = [ROOT];
  for (const segment of segments) {
    const next = [];
    for (const dir of dirs) {
      if (segment === '**') next.push(...walkDirs(dir, WALK_DEPTH));
      else if (segment.includes('*')) {
        const matcher = new RegExp(`^${segment.split('*').map(escapeRegExp).join('.*')}$`);
        for (const child of listDirs(dir)) if (matcher.test(child)) next.push(join(dir, child));
      } else {
        const candidate = join(dir, segment);
        if (existsSync(candidate) && statSync(candidate).isDirectory()) next.push(candidate);
      }
    }
    dirs = [...new Set(next)];
  }
  return dirs.filter((dir) => existsSync(join(dir, 'package.json')));
}

function workspaceGlobs() {
  const globs = [];
  const yamlPath = join(ROOT, 'pnpm-workspace.yaml');
  if (existsSync(yamlPath)) {
    let inPackages = false;
    for (const raw of readFileSync(yamlPath, 'utf-8').split('\n')) {
      const line = raw.replace(/#.*$/, '').trimEnd();
      if (/^packages\s*:/.test(line)) {
        inPackages = true;
        continue;
      }
      if (!inPackages) continue;
      const item = line.match(/^\s+-\s*['"]?([^'"]+?)['"]?\s*$/);
      if (item) globs.push(item[1]);
      else if (line.trim() && !/^\s/.test(line)) inPackages = false;
    }
  }
  const rootPackage = readJson(join(ROOT, 'package.json'));
  const workspaces = rootPackage?.workspaces;
  if (Array.isArray(workspaces)) globs.push(...workspaces);
  else if (workspaces && Array.isArray(workspaces.packages)) globs.push(...workspaces.packages);
  return globs;
}

/** name -> { dir, dependents: string[] } for every workspace package. */
function discoverWorkspace() {
  const globs = workspaceGlobs();
  const included = new Set();
  const excluded = new Set();
  for (const pattern of globs) {
    if (pattern.startsWith('!')) for (const dir of expandGlob(pattern.slice(1))) excluded.add(dir);
    else for (const dir of expandGlob(pattern)) included.add(dir);
  }
  const packages = new Map();
  for (const dir of included) {
    if (excluded.has(dir)) continue;
    const manifest = readJson(join(dir, 'package.json'));
    if (!manifest?.name) continue;
    const dependencies = new Set();
    for (const field of ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']) {
      for (const name of Object.keys(manifest[field] ?? {})) dependencies.add(name);
    }
    packages.set(manifest.name, { dir, dependencies, dependents: [] });
  }
  for (const [name, entry] of packages) {
    for (const dependency of entry.dependencies) {
      const target = packages.get(dependency);
      if (target) target.dependents.push(name);
    }
  }
  for (const entry of packages.values()) entry.dependents.sort();
  return packages;
}

/** The nearest package.json above the file, as { name, dir } relative to ROOT. */
function owningPackage(file) {
  let dir = dirname(join(ROOT, file));
  while (dir.startsWith(ROOT)) {
    const manifestPath = join(dir, 'package.json');
    if (existsSync(manifestPath)) {
      const manifest = readJson(manifestPath);
      return { name: manifest?.name ?? null, dir: relative(ROOT, dir) || '.' };
    }
    if (dir === ROOT) break;
    dir = dirname(dir);
  }
  return { name: null, dir: '.' };
}

function touchedText(file, base) {
  if (base) {
    const diff = git(['diff', `${base}...HEAD`, '--', file]);
    return diff
      .split('\n')
      .filter((line) => /^[+-]/.test(line) && !/^(?:\+\+\+|---)/.test(line))
      .map((line) => line.slice(1))
      .join('\n');
  }
  const path = join(ROOT, file);
  return existsSync(path) ? readFileSync(path, 'utf-8') : '';
}

function exportedNames(text) {
  return [...text.matchAll(EXPORT_RE)].map((match) => match[1]).filter((name) => !SKIP_NAME.test(name));
}

function consumersOf(file, text) {
  let names = new Set(exportedNames(text));
  // A change to a style constant inside an exported object shows no `export`
  // in the diff; fall back to the whole file's exports.
  if (names.size === 0 && existsSync(join(ROOT, file))) {
    names = new Set(exportedNames(readFileSync(join(ROOT, file), 'utf-8')));
  }
  const consumers = [];
  for (const name of [...names].slice(0, MAX_SYMBOLS_PER_FILE)) {
    const hits = git(['grep', '-l', '-w', '-e', name, 'HEAD'])
      .split('\n')
      .filter(Boolean)
      .map((line) => line.replace(/^HEAD:/, ''))
      .filter((hit) => hit !== file && SOURCE_RE.test(hit) && !TEST_RE.test(hit));
    if (hits.length > 0) consumers.push({ name, count: hits.length, sample: hits.slice(0, SAMPLE_SIZE) });
  }
  consumers.sort((a, b) => b.count - a.count);
  return consumers;
}

// ---- collect the file list
let base = null;
let files;
if (options.diff) {
  base = options.base ?? detectBase();
  if (!base) fail('cannot detect the default branch; pass --diff BASE');
  if (!gitOk(['rev-parse', '--verify', '-q', `${base}^{commit}`])) fail(`unknown base ${base}`);
  files = git(['diff', '--name-only', `${base}...HEAD`]).split('\n');
} else {
  // Explicit paths are relative to --root (default: the current directory).
  // Resolve symlinked directories first so the path lands inside ROOT.
  let fileBase = resolve(options.root);
  try {
    fileBase = realpathSync(fileBase);
  } catch {
    // keep the unresolved path; git already accepted it
  }
  files = options.files.map((file) => relative(ROOT, resolve(fileBase, file)));
}
// Test, spec, and story files are neither scanned nor counted: a selector or
// default inside a test reaches no production consumer.
files = files.map((file) => file.trim()).filter((file) => file && SOURCE_RE.test(file) && !TEST_RE.test(file));

const workspace = discoverWorkspace();
const results = [];
for (const file of files) {
  const text = touchedText(file, base);
  if (!text) continue;
  const owner = owningPackage(file);
  const dependents = owner.name ? (workspace.get(owner.name)?.dependents ?? []) : [];
  const alwaysOn = ALWAYS_ON.filter(([pattern]) => pattern.test(text)).map(([, why]) => why);
  const overrides = OVERRIDE.filter(([pattern]) => pattern.test(text)).map(([, why]) => why);
  // Consumers are searched when the reach can leave the owning package: the
  // file is flagged, the package has dependents, or there is no workspace at
  // all. Inside one application the application's own review already sees
  // its consumers, and the search is the expensive step on a large tree.
  const searchConsumers = alwaysOn.length > 0 || overrides.length > 0 || workspace.size === 0 || dependents.length > 0;
  const consumers = searchConsumers ? consumersOf(file, text) : [];
  if (consumers.length === 0 && alwaysOn.length === 0 && overrides.length === 0) continue;
  results.push({
    file,
    package: owner.name,
    dependents,
    always_on: alwaysOn,
    overrides,
    consumers,
    flagged: alwaysOn.length > 0 || overrides.length > 0,
  });
}

const flagged = results.filter((entry) => entry.flagged);
const consumerOnly = results
  .filter((entry) => !entry.flagged)
  .sort((a, b) => (b.consumers[0]?.count ?? 0) - (a.consumers[0]?.count ?? 0));
const shown = options.all ? results : flagged.length > 0 ? flagged : consumerOnly.slice(0, ORIENTATION_SIZE);

if (options.json) {
  console.log(
    JSON.stringify(
      {
        base,
        files_scanned: files.length,
        flagged_count: flagged.length,
        consumer_only_count: consumerOnly.length,
        shown: shown.map((entry) => entry.file),
        results,
      },
      null,
      2,
    ),
  );
  process.exit(flagged.length > 0 ? 1 : 0);
}

if (files.length === 0) {
  console.log('No changed source files.');
  process.exit(0);
}
if (results.length === 0) {
  console.log('No reach-widening change: no shared export, default, or override touched.');
  process.exit(0);
}

const scopeNote = options.all
  ? ''
  : flagged.length > 0
    ? ' - showing flagged files only (use --all for everything)'
    : ' - nothing flagged; showing the widest consumer lists (use --all for everything)';
console.log(`## Change reach${base ? ` (base: ${base})` : ''}`);
console.log(
  `${files.length} source file(s) - flagged ${flagged.length} - consumers only ${consumerOnly.length}${scopeNote}`,
);
console.log();
for (const entry of shown) {
  console.log(`### ${entry.file}`);
  if (entry.package) {
    const hidden = entry.dependents.length - DEPENDENTS_SHOWN;
    const names = entry.dependents.slice(0, DEPENDENTS_SHOWN).join(', ') + (hidden > 0 ? ` and ${hidden} more` : '');
    const dependents = entry.dependents.length ? ` - dependent packages ${entry.dependents.length}: ${names}` : '';
    console.log(`- package: \`${entry.package}\`${dependents}`);
  }
  if (entry.always_on.length) {
    console.log('- FLAG cannot opt out - applies to every consumer of this file');
    for (const why of entry.always_on) console.log(`  - ${why}`);
  }
  if (entry.overrides.length) {
    console.log('- FLAG overrides a value - did this remove the cause or hide the observation?');
    for (const why of entry.overrides) console.log(`  - ${why}`);
  }
  if (entry.consumers.length) {
    console.log('- consumers (files referencing each symbol; upper bound)');
    for (const consumer of entry.consumers) {
      console.log(`  - \`${consumer.name}\` - ${consumer.count} file(s) (e.g. ${consumer.sample.join(', ')})`);
    }
  }
  console.log();
}
console.log('---');
console.log('Counts are upper bounds: a common name inflates them; confirm with the sample paths.');
if (flagged.length > 0) {
  console.log('Flags present: record the reach on the pull request and answer the five scope questions.');
} else {
  console.log('No flags: shared exports were touched, so skim the consumers; the five questions can be skipped.');
}
process.exit(flagged.length > 0 ? 1 : 0);
