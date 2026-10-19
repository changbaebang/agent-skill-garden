#!/usr/bin/env node
/**
 * Profile matrix: load one page under several client profiles and measure the
 * same element in each, so a platform-conditional defect can be reproduced in
 * a desktop browser instead of on a stack of real devices.
 *
 * A profile is what the page uses to decide it is inside an embedded client:
 * a user-agent string, attributes the client sets on elements, and CSS custom
 * properties the client or operating system supplies. Profiles are data in a
 * JSON file (see references/profile-matrix.md); nothing about any particular
 * application is built in.
 *
 * CSS custom properties are injected through a stylesheet rule on :root, never
 * as inline styles. An inline injection would outrank the page's own code, and
 * the page's own code is what must stay observable: a polyfill that writes the
 * same property inline is exactly what masks a defect on one platform. The
 * report records both the computed value and any inline value so a masked
 * profile shows up as a difference in inputs.
 *
 * Usage:
 *   node profile_matrix.mjs --url URL --profiles profiles.json \
 *     --selector "header" --out ./matrix-out
 *
 * Options:
 *   --only key1,key2    run a subset of profile keys
 *   --wait MS           settle time after DOMContentLoaded (default 4000)
 *   --props a,b,c       computed style properties to record
 *   --clip HEIGHT       screenshot height from the top edge (default 300)
 *   --playwright PATH   module path when resolution from the current directory fails
 *                       (the PLAYWRIGHT_MODULE environment variable does the same)
 *
 * Output: one screenshot per profile and measurements.json in --out, plus a
 * markdown table on stdout. Feed measurements.json to measurement_report.py to
 * see which fields diverge between profiles.
 */
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const DEFAULT_PROPS = 'paddingTop,paddingBottom,marginTop,minHeight,height,display,position,top';

function arg(key, fallback) {
  const index = process.argv.indexOf(`--${key}`);
  if (index > -1 && index + 1 < process.argv.length) return process.argv[index + 1];
  return fallback;
}

function fail(message) {
  console.error(`[profile-matrix] ${message}`);
  process.exit(2);
}

function splitList(value) {
  return String(value)
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function loadProfiles(path) {
  let parsed;
  try {
    parsed = JSON.parse(readFileSync(resolve(path), 'utf-8'));
  } catch (error) {
    fail(`cannot read profiles file: ${error.message}`);
  }
  if (!Array.isArray(parsed) || parsed.length === 0) fail('profiles must be a non-empty JSON array');
  for (const profile of parsed) {
    if (!profile || typeof profile.key !== 'string' || typeof profile.userAgent !== 'string') {
      fail('each profile needs a string "key" and a string "userAgent"');
    }
  }
  return parsed;
}

async function loadPlaywright() {
  const explicit = arg('playwright', process.env.PLAYWRIGHT_MODULE);
  let modulePath = explicit ? resolve(explicit) : null;
  if (!modulePath) {
    try {
      const require = createRequire(resolve(process.cwd(), 'package.json'));
      modulePath = require.resolve('playwright');
    } catch {
      fail(
        'playwright could not be resolved from the current directory; run from a project that depends on it or pass --playwright PATH',
      );
    }
  }
  const loaded = await import(pathToFileURL(modulePath).href);
  const chromium = loaded.chromium ?? loaded.default?.chromium;
  if (!chromium) fail(`module at ${modulePath} does not export chromium`);
  return chromium;
}

const url = arg('url');
const profilesPath = arg('profiles');
const selector = arg('selector', 'body');
const outDir = resolve(arg('out', `profile-matrix-${Date.now()}`));
const waitMs = Number(arg('wait', '4000'));
const clipHeight = Number(arg('clip', '300'));
const only = arg('only');
const props = splitList(arg('props', DEFAULT_PROPS));

if (!url) fail('--url is required');
if (!profilesPath) fail('--profiles is required (a JSON array; see references/profile-matrix.md)');

const profiles = loadProfiles(profilesPath);
const selected = only ? profiles.filter((profile) => splitList(only).includes(profile.key)) : profiles;
if (selected.length === 0) fail('--only matched no profile keys');

const chromium = await loadPlaywright();
mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch({ headless: true });
const results = [];

for (const profile of selected) {
  const viewport = profile.viewport ?? { width: 390, height: 844 };
  const context = await browser.newContext({
    userAgent: profile.userAgent,
    viewport,
    isMobile: profile.isMobile ?? true,
    hasTouch: profile.hasTouch ?? true,
    deviceScaleFactor: profile.deviceScaleFactor ?? 2,
    ignoreHTTPSErrors: true,
  });
  const page = await context.newPage();
  const injection = {
    attributes: Array.isArray(profile.attributes) ? profile.attributes : [],
    cssVariables: profile.cssVariables && typeof profile.cssVariables === 'object' ? profile.cssVariables : {},
    css: typeof profile.css === 'string' ? profile.css : '',
  };

  await page.addInitScript((inject) => {
    const pick = (sel) => {
      if (sel === 'html') return document.documentElement;
      if (sel === 'body') return document.body;
      return document.querySelector(sel);
    };
    const apply = () => {
      for (const attribute of inject.attributes) {
        const target = pick(attribute.selector);
        if (target) target.setAttribute(attribute.name, attribute.value);
      }
      const declarations = Object.entries(inject.cssVariables)
        .map(([name, value]) => `${name}:${value}`)
        .join(';');
      const style = document.createElement('style');
      style.setAttribute('data-profile-matrix', '');
      style.textContent = (declarations ? `:root{${declarations}}` : '') + inject.css;
      (document.head ?? document.documentElement).appendChild(style);
    };
    if (document.body) apply();
    else document.addEventListener('DOMContentLoaded', apply);
  }, injection);

  let error = null;
  try {
    await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.waitForTimeout(waitMs);
  } catch (caught) {
    error = String(caught).split('\n')[0];
  }

  const measured = await page.evaluate(
    ({ sel, styleProps, variableNames, attributes }) => {
      const pick = (s) => {
        if (s === 'html') return document.documentElement;
        if (s === 'body') return document.body;
        return document.querySelector(s);
      };
      const rootStyle = getComputedStyle(document.documentElement);
      const cssVariables = {};
      for (const name of variableNames) {
        cssVariables[name] = {
          computed: rootStyle.getPropertyValue(name).trim(),
          inline: document.documentElement.style.getPropertyValue(name).trim() || null,
        };
      }
      const attributeValues = {};
      for (const attribute of attributes) {
        const target = pick(attribute.selector);
        attributeValues[`${attribute.selector}[${attribute.name}]`] = target
          ? target.getAttribute(attribute.name)
          : null;
      }
      const element = document.querySelector(sel);
      const base = { url: location.href, cssVariables, attributes: attributeValues, found: Boolean(element) };
      if (!element) return base;
      const computed = getComputedStyle(element);
      const rect = element.getBoundingClientRect();
      const style = {};
      for (const prop of styleProps) style[prop] = computed[prop];
      return {
        ...base,
        style,
        rect: { top: Math.round(rect.top), height: Math.round(rect.height), width: Math.round(rect.width) },
        className: typeof element.className === 'string' ? element.className : '',
      };
    },
    {
      sel: selector,
      styleProps: props,
      variableNames: Object.keys(injection.cssVariables),
      attributes: injection.attributes,
    },
  );

  try {
    await page.screenshot({
      path: `${outDir}/${profile.key}.png`,
      clip: { x: 0, y: 0, width: viewport.width, height: Math.min(clipHeight, viewport.height) },
    });
  } catch (caught) {
    error = error ?? `screenshot failed: ${String(caught).split('\n')[0]}`;
  }

  results.push({ key: profile.key, label: profile.label ?? profile.key, error, ...measured });
  await context.close();
}

await browser.close();
writeFileSync(
  `${outDir}/measurements.json`,
  JSON.stringify({ url, selector, properties: props, results }, null, 2),
);

console.log(`## Profile matrix: \`${selector}\` at ${url}\n`);
console.log('| Profile | Found | Variables (computed / inline) | Style | Height | Note |');
console.log('|---|---|---|---|---|---|');
for (const result of results) {
  const variables = Object.entries(result.cssVariables ?? {})
    .map(([name, value]) => `${name}: ${value.computed || '-'} / ${value.inline ?? '-'}`)
    .join('; ');
  const style = Object.entries(result.style ?? {})
    .map(([name, value]) => `${name}=${value}`)
    .join(' ');
  const note = result.error ? `error: ${result.error.slice(0, 60)}` : '';
  console.log(
    `| ${result.label} | ${result.found ? 'yes' : 'no'} | ${variables || '-'} | ${style || '-'} | ${
      result.rect ? `${result.rect.height}px` : '-'
    } | ${note} |`,
  );
}
console.log(`\nScreenshots and measurements.json: ${outDir}`);
console.log('A single clean profile may be masked rather than fixed; compare the values, not the pictures.');
