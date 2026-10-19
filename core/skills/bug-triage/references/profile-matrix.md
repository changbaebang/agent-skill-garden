# Profile matrix

Load one page under several client profiles and measure the same element in
each, so a platform-conditional defect can be reproduced in a desktop browser.
The harness is `scripts/profile_matrix.mjs`; the comparison is
`scripts/measurement_report.py`.

## What a profile is

Everything the page uses to decide it is inside an embedded client: the
user-agent string, attributes the client sets on elements, and CSS custom
properties the client or the operating system supplies (safe-area insets are
the common case). Profiles are data in a JSON file you keep with the project
or in your local notes; the harness has no application built in.

```json
[
  {
    "key": "mobile-web",
    "label": "Mobile browser, not embedded",
    "userAgent": "a mobile browser user agent copied from a real device"
  },
  {
    "key": "ios-embedded",
    "label": "Embedded client on iOS",
    "userAgent": "the same browser user agent plus the token the client appends",
    "attributes": [{ "selector": "body", "name": "data-client", "value": "embedded" }],
    "cssVariables": { "--safe-area-inset-top": "59px", "--safe-area-inset-bottom": "34px" }
  },
  {
    "key": "android-embedded",
    "label": "Embedded client on Android",
    "userAgent": "an Android browser user agent plus the client token",
    "attributes": [{ "selector": "body", "name": "data-client", "value": "embedded" }],
    "cssVariables": { "--safe-area-inset-top": "59px", "--safe-area-inset-bottom": "34px" }
  }
]
```

Optional per-profile fields: `css` (a raw stylesheet string), `viewport`
(`{ "width", "height" }`), `isMobile`, `hasTouch`, `deviceScaleFactor`.

Take the user-agent strings and attribute names from the web code that reads
them, so the matrix exercises the real branch conditions.

## Run

From a project whose dependencies include the Playwright library (the harness
drives a Chromium build through it):

```bash
node scripts/profile_matrix.mjs \
  --url "https://host/path?with=the-reporters-parameters" \
  --profiles ./profiles.json \
  --selector "header" \
  --out ./matrix-out
python3 scripts/measurement_report.py ./matrix-out/measurements.json
```

Pass `--playwright PATH` or set `PLAYWRIGHT_MODULE` when the library cannot be
resolved from the current directory. `--only key1,key2` runs a subset,
`--props` chooses the computed style properties to record, `--wait` sets the
settle time after load.

## Why variables are injected through a stylesheet

The harness writes CSS custom properties as a `:root` rule in a stylesheet,
never as inline styles on the root element. An inline injection outranks the
page's own code, and the page's own code is what you need to observe: when a
web-side polyfill writes the same property inline (often to zero), that write
is exactly what masks the defect on one platform. With the stylesheet rule in
place the polyfill still wins, the report shows both the computed value and
the inline value, and the masked profile becomes visible as a difference in
inputs rather than a mysteriously clean screenshot.

## Read the result

`measurement_report.py` prints fields as rows and profiles as columns and marks
each row whose values differ. When exactly one profile differs it names that
profile. Treat it as the next place to look, not as the platform that is fine:
confirm whether that profile is fixed or merely masked by comparing its inputs
(inline variable values, attribute values) with the others.

Screenshots are for the report; the verdict comes from the values.
