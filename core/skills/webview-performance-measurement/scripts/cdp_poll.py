#!/usr/bin/env python3
"""Poll a page-side timing harness over the DevTools protocol without an inspector.

The page under test keeps an array of timing samples in sessionStorage. This
script connects to the browser's DevTools socket (forwarded from the device with
adb), finds the page by a URL substring, optionally asks the harness to start a
run, and polls the storage entry until the requested number of samples exists.
It then prints nearest-rank p50/p75/p90 for every numeric field and writes the
raw samples to a JSON file.

Console capture is deliberately not used: enabling the runtime domain replays
old console history, and console streaming breaks when the page reloads.
Storage survives reloads, so polling it is robust.

Network access happens only inside the Session class and main(); every other
function is pure so it can be tested offline. Requires the third-party package
``websocket-client`` at run time only.

Usage:
    python3 cdp_poll.py --match /page-path --storage-key perf-run --samples 100 \
        --start-fn __perfRun --stop-fn __perfStop --out samples.json
    python3 cdp_poll.py --list-targets
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Sequence

DEFAULT_PORT = 9222
DEFAULT_PERCENTILES = (0.5, 0.75, 0.9)


# --------------------------------------------------------------------------- pure


def nearest_rank(values: Sequence[float], p: float) -> Optional[float]:
    """sorted[ceil(n * p) - 1]; returns None for an empty sequence."""
    ordered = sorted(values)
    if not ordered:
        return None
    if not 0.0 <= p <= 1.0:
        raise ValueError("percentile must be between 0 and 1")
    rank = max(math.ceil(len(ordered) * p), 1)
    return float(ordered[rank - 1])


def find_samples(obj: Any) -> Optional[List[dict]]:
    """Locate the sample list inside whatever JSON shape the harness stores.

    Accepts a bare list of objects, an object with a ``samples`` list, or any
    nesting that eventually holds one.
    """
    if isinstance(obj, list):
        if all(isinstance(item, dict) for item in obj):
            return obj
        return None
    if isinstance(obj, dict):
        candidate = obj.get("samples")
        if isinstance(candidate, list):
            return candidate
        for value in obj.values():
            found = find_samples(value)
            if found is not None:
                return found
    return None


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def numeric_keys(samples: Sequence[dict], preferred: Optional[Sequence[str]] = None) -> List[str]:
    """Fields that carry at least one numeric value, preferred names first.

    Remaining fields keep first-seen order so the table reads like the harness
    recorded it.
    """
    seen: List[str] = []
    for sample in samples:
        for key, value in sample.items():
            if _is_number(value) and key not in seen:
                seen.append(key)
    ordered = [key for key in (preferred or []) if key in seen]
    ordered.extend(key for key in seen if key not in ordered)
    return ordered


def summarize(
    samples: Sequence[dict],
    keys: Sequence[str],
    percentiles: Sequence[float] = DEFAULT_PERCENTILES,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key in keys:
        values = [sample[key] for sample in samples if _is_number(sample.get(key))]
        if not values:
            continue
        row: Dict[str, Any] = {"segment": key, "n": len(values)}
        for p in percentiles:
            row[f"p{int(round(p * 100))}"] = nearest_rank(values, p)
        rows.append(row)
    return rows


def render_rows(rows: Sequence[Dict[str, Any]], percentiles: Sequence[float] = DEFAULT_PERCENTILES) -> List[str]:
    labels = [f"p{int(round(p * 100))}" for p in percentiles]
    width = max([len("segment")] + [len(str(row["segment"])) for row in rows])
    lines = ["  ".join(["segment".ljust(width), "n".rjust(5)] + [label.rjust(8) for label in labels])]
    for row in rows:
        cells = [str(row["segment"]).ljust(width), str(row["n"]).rjust(5)]
        for label in labels:
            value = row.get(label)
            cells.append(("-" if value is None else f"{value:.0f}").rjust(8))
        lines.append("  ".join(cells))
    return lines


def select_target(target_infos: Sequence[dict], match: str) -> Optional[dict]:
    """First page target whose URL contains ``match``; other target types are ignored."""
    for info in target_infos:
        if info.get("type") != "page":
            continue
        if match in (info.get("url") or ""):
            return info
    return None


def page_targets(target_infos: Sequence[dict]) -> List[dict]:
    return [info for info in target_infos if info.get("type") == "page"]


def storage_read_expression(key_substring: str) -> str:
    """JS that returns the first sessionStorage value whose key contains the substring."""
    needle = json.dumps(key_substring)
    return (
        "(function(){try{for(var i=0;i<sessionStorage.length;i++){"
        "var k=sessionStorage.key(i);"
        f"if(k&&k.indexOf({needle})>=0)return sessionStorage.getItem(k);}}}}"
        "catch(e){}return null;})()"
    )


def probe_expression(function_name: str) -> str:
    return f"typeof window[{json.dumps(function_name)}]"


def call_expression(function_name: str, *args: Any) -> str:
    rendered = ",".join(json.dumps(arg) for arg in args)
    name = json.dumps(function_name)
    return f"(function(){{try{{var f=window[{name}];if(typeof f==='function')f({rendered});}}catch(e){{}}}})()"


def parse_samples(raw: Optional[str]) -> Optional[List[dict]]:
    if not raw:
        return None
    try:
        return find_samples(json.loads(raw))
    except (TypeError, ValueError):
        return None


def poll(
    read: Callable[[], Optional[List[dict]]],
    target_count: int,
    *,
    timeout_s: float,
    interval_s: float,
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
    progress: Optional[Callable[[int, List[dict]], None]] = None,
) -> List[dict]:
    """Keep the longest sample list seen until ``target_count`` arrive or time runs out.

    A read that fails (returns None) during a reload is ignored; a shorter list
    after a longer one is ignored too, so a harness that resets storage cannot
    make the count go backwards.
    """
    best: List[dict] = []
    deadline = now() + timeout_s
    last_reported = -1
    while True:
        if len(best) >= target_count:
            break
        if now() >= deadline:
            break
        sleep(interval_s)
        samples = read()
        if samples is not None and len(samples) > len(best):
            best = list(samples)
            if progress is not None and len(best) != last_reported:
                last_reported = len(best)
                progress(len(best), best)
    return best[:target_count]


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll a timing harness's sessionStorage over the DevTools protocol.",
    )
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="local port forwarded to the device DevTools socket")
    parser.add_argument("--match", help="URL substring that identifies the page target")
    parser.add_argument("--storage-key", help="substring of the sessionStorage key the harness writes")
    parser.add_argument("--samples", type=int, default=100, help="number of samples to collect")
    parser.add_argument("--start-fn", help="window function that starts a run; called with --samples plus --margin")
    parser.add_argument("--stop-fn", help="window function that stops a run; called before seeding and after collection")
    parser.add_argument("--margin", type=int, default=8, help="extra runs requested so the harness does not stop before the count is reached")
    parser.add_argument("--interval", type=float, default=1.5, help="seconds between storage reads")
    parser.add_argument("--timeout", type=float, default=600.0, help="give up after this many seconds")
    parser.add_argument("--progress-key", help="numeric field to show in progress lines (default: first numeric field)")
    parser.add_argument("--segments", nargs="*", default=None, help="field names to print first, in this order")
    parser.add_argument("--out", help="where to write raw samples (default: samples_n<count>.json in the working directory)")
    parser.add_argument("--list-targets", action="store_true", help="print page targets and exit")
    parser.add_argument("--json", action="store_true", help="print the summary as JSON instead of a table")
    args = parser.parse_args(argv)
    if not args.list_targets:
        missing = [name for name, value in (("--match", args.match), ("--storage-key", args.storage_key)) if not value]
        if missing:
            parser.error("required: " + ", ".join(missing))
    if args.samples <= 0:
        parser.error("--samples must be positive")
    return args


# ------------------------------------------------------------------------ network


class Session:
    """Thin DevTools protocol client over one browser websocket.

    The origin header is suppressed because recent browsers reject DevTools
    websockets that carry one. Page targets are enumerated with
    Target.getTargets instead of the HTTP target list, which some browser
    versions return empty on Android.
    """

    def __init__(self, port: int, timeout_s: float = 8.0) -> None:
        try:
            import websocket  # type: ignore
        except ImportError as error:  # pragma: no cover - depends on the environment
            raise SystemExit("websocket-client is required: pip install --user websocket-client") from error
        version_url = f"http://127.0.0.1:{port}/json/version"
        with urllib.request.urlopen(version_url, timeout=5) as response:
            browser_ws = json.load(response)["webSocketDebuggerUrl"]
        self._ws = websocket.create_connection(browser_ws, timeout=timeout_s, suppress_origin=True)
        self._timeout_s = timeout_s
        self._next_id = 0
        self.session_id: Optional[str] = None

    def call(self, method: str, params: Optional[dict] = None, session_id: Optional[str] = None) -> dict:
        self._next_id += 1
        message: Dict[str, Any] = {"id": self._next_id, "method": method, "params": params or {}}
        if session_id:
            message["sessionId"] = session_id
        self._ws.send(json.dumps(message))
        self._ws.settimeout(self._timeout_s)
        while True:
            try:
                reply = json.loads(self._ws.recv())
            except Exception as error:  # noqa: BLE001 - any socket failure is reported the same way
                return {"__error__": str(error)}
            if reply.get("id") == self._next_id:
                return reply

    def targets(self) -> List[dict]:
        reply = self.call("Target.getTargets")
        return reply.get("result", {}).get("targetInfos", [])

    def attach(self, target_id: str) -> str:
        reply = self.call("Target.attachToTarget", {"targetId": target_id, "flatten": True})
        session_id = reply.get("result", {}).get("sessionId")
        if not session_id:
            raise SystemExit(f"attach failed: {reply}")
        self.session_id = session_id
        return session_id

    def evaluate(self, expression: str) -> Any:
        reply = self.call(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True, "awaitPromise": False},
            self.session_id,
        )
        if "__error__" in reply or "exceptionDetails" in reply.get("result", {}):
            return None
        return reply.get("result", {}).get("result", {}).get("value")

    def close(self) -> None:
        try:
            self._ws.close()
        except Exception:  # noqa: BLE001
            pass


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    session = Session(args.port)
    try:
        infos = session.targets()
        if args.list_targets:
            for info in page_targets(infos):
                print(info.get("url", ""))
            return 0

        target = select_target(infos, args.match)
        if target is None:
            print(f"no page target contains {args.match!r}; current page targets:", file=sys.stderr)
            for info in page_targets(infos):
                print("  -", info.get("url", ""), file=sys.stderr)
            return 1
        print(f"attached to {target.get('url', '')}", flush=True)
        session.attach(target["targetId"])

        read_expression = storage_read_expression(args.storage_key)

        def read() -> Optional[List[dict]]:
            return parse_samples(session.evaluate(read_expression))

        if args.start_fn:
            if session.evaluate(probe_expression(args.start_fn)) != "function":
                print(
                    f"{args.start_fn} is not defined on the page; confirm the harness is on this build "
                    "and that its query switch is set.",
                    file=sys.stderr,
                )
                return 1
            if args.stop_fn:
                session.evaluate(call_expression(args.stop_fn))
            session.evaluate(call_expression(args.start_fn, args.samples + args.margin))
            print(f"run seeded for {args.samples + args.margin} iterations; collecting {args.samples}", flush=True)
        else:
            print(f"no start function given; polling existing storage for {args.samples} samples", flush=True)

        def progress(count: int, samples: List[dict]) -> None:
            if count % 10 != 0 and count < args.samples:
                return
            key = args.progress_key or (numeric_keys(samples)[:1] or [None])[0]
            if key is None:
                print(f"  {count}/{args.samples}", flush=True)
                return
            values = [sample[key] for sample in samples if _is_number(sample.get(key))]
            median = nearest_rank(values, 0.5)
            shown = "-" if median is None else f"{median:.0f}"
            print(f"  {count}/{args.samples}  {key} p50 {shown}", flush=True)

        samples = poll(
            read,
            args.samples,
            timeout_s=args.timeout,
            interval_s=args.interval,
            progress=progress,
        )
        if args.stop_fn:
            session.evaluate(call_expression(args.stop_fn))
    finally:
        session.close()

    if not samples:
        print("no samples collected; check the page, the storage key, and the harness state", file=sys.stderr)
        return 1
    if len(samples) < args.samples:
        print(f"timed out with {len(samples)}/{args.samples} samples; numbers below are partial", file=sys.stderr)

    keys = numeric_keys(samples, args.segments)
    rows = summarize(samples, keys)
    out_path = args.out or f"samples_n{len(samples)}.json"
    with open(out_path, "w", encoding="utf-8") as handle:
        json.dump(samples, handle)

    if args.json:
        print(json.dumps({"n": len(samples), "method": "nearest-rank", "rows": rows, "raw": out_path}, indent=2))
    else:
        print(f"\ncollected n={len(samples)} (nearest-rank percentiles, ms)")
        for line in render_rows(rows):
            print(line)
        print(f"\nraw samples -> {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
