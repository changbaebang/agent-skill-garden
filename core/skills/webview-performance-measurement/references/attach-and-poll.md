# Attaching without the inspector, then polling

Every value below that names a host, port, package, storage key, or function
comes from the project under test or the environment profile. Nothing here is
a default to copy.

## 1. Forward the device DevTools socket

```bash
adb devices                                   # pick the serial
adb -s SERIAL forward tcp:9222 localabstract:chrome_devtools_remote
```

`chrome_devtools_remote` is the socket name of the standalone browser. An
embedded webview exposes `webview_devtools_remote_<pid>` instead, and only when
the host application has enabled webview debugging. List what the device offers:

```bash
adb -s SERIAL shell cat /proc/net/unix | grep devtools_remote
```

Confirm the forward works before touching the page:

```bash
curl -s http://127.0.0.1:9222/json/version
```

An empty `/json/list` while `/json/version` answers is normal on recent browser
versions. Do not read it as "no pages": enumerate pages through the protocol
(`Target.getTargets`), which the script does.

## 2. Open the page with the harness switch on

```bash
adb -s SERIAL shell "am start -a android.intent.action.VIEW \
  -d 'https://TEST_HOST/PATH?HARNESS_SWITCH=1' BROWSER_PACKAGE"
```

Reaching the page from the device:

- An emulator reaches the host machine's loopback at `10.0.2.2`. If the page
  needs cookies or an authenticated origin, that address will not carry them.
- A physical device cannot reach your loopback at all. Route it through a local
  proxy on the same network that preserves the application's origin, so cookies
  and the development certificate behave as they would in the real environment.
  The proxy host, port, and test hostname belong in the environment profile.

## 3. Poll the harness storage

```bash
python3 scripts/cdp_poll.py \
  --match PAGE_URL_SUBSTRING \
  --storage-key HARNESS_STORAGE_KEY_SUBSTRING \
  --samples 100 \
  --start-fn HARNESS_START_FUNCTION --stop-fn HARNESS_STOP_FUNCTION \
  --out samples_before.json
```

- `--list-targets` prints the page URLs the browser exposes when you are unsure
  what to match.
- Omit `--start-fn` when the harness runs on its own; the script then only reads.
- `--margin` (default 8) is added to the requested run count so the harness
  does not stop itself before the script has read the final samples.
- `--segments a b c` puts those fields first in the table; `--progress-key`
  picks the field shown while collecting.
- `--json` emits the summary as JSON for a later before/after comparison.

The script connects with the websocket origin header suppressed, attaches to the
page target in flat mode, and never enables the console domain. It tolerates
evaluate failures during reloads and ignores a sample list that got shorter.

## 4. Clean up

```bash
adb -s SERIAL forward --remove tcp:9222
```

## Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| Device missing from the desktop inspector page | Inspector-side discovery, not the device | Skip the inspector; forward the socket directly |
| `403 Rejected WebSocket from origin` | Browser rejects DevTools websockets that carry an origin header | Connect with the origin suppressed (the script does) |
| `/json/list` returns `[]` | Known behavior on recent browser versions | Use `Target.getTargets` (the script does) |
| Start function "is not defined" | Wrong build, wrong revision, or the harness switch is not in the URL | Confirm the harness exists on this revision and which switch it parses |
| Count stuck below the target | Harness stopped early, page navigated away, or storage cleared | Raise `--margin`, re-open the page, re-run |
| Old results appear immediately | Console history replay | Not possible with storage polling; if you see this you are reading the console |
