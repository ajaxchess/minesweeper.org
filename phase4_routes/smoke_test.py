"""
phase4_routes.smoke_test — Post-deploy smoke test for the analytics API.

Hits every Phase 4 endpoint against a running server, validates response codes,
and prints a one-line PASS/FAIL summary per route.

Usage:
    python -m phase4_routes.smoke_test \\
        --base-url http://localhost:8000 \\
        --cookie "session=<your-session-cookie>"

Or with environment variables:
    SMOKE_BASE_URL=https://minesweeper.org \\
    SMOKE_COOKIE='session=...' \\
    python -m phase4_routes.smoke_test

Exit codes:
    0 — all endpoints returned a success-shape response (200, 404 "no games yet",
        or 425 "analysis pending" are all acceptable; everything else fails)
    1 — one or more endpoints returned an unexpected status or invalid JSON

Designed to run from cron after a deploy so any regression is caught in seconds.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(2)


# Status codes we consider "the endpoint is alive and responding sensibly"
ACCEPTABLE_STATUSES = {200, 404, 425}

# Expected top-level fields per endpoint — used as a shape sanity check
EXPECTED_FIELDS = {
    "/api/bootcamp/diagnosis":  ["current_level", "levels", "blockers"],
    "/api/bootcamp/level/2":    ["level", "habits", "drills", "graduation"],
    "/api/radar":               ["axes", "insights"],
    "/api/patterns/fluency":    ["overall_score", "patterns", "weekly_plan"],
    "/api/replays":             ["replays", "total"],
    "/api/heatmap":             ["cells", "cause_breakdown", "region_breakdown"],
}


@dataclass
class CheckResult:
    endpoint: str
    status: int
    ok: bool
    note: str = ""


def run_check(
    session: requests.Session, base_url: str, path: str, params: dict | None = None
) -> CheckResult:
    url = base_url.rstrip("/") + path
    try:
        r = session.get(url, params=params, timeout=10)
    except requests.RequestException as e:
        return CheckResult(path, 0, False, f"request failed: {e}")

    if r.status_code not in ACCEPTABLE_STATUSES:
        return CheckResult(path, r.status_code, False, "unexpected status")

    # On 200, also check the response shape
    if r.status_code == 200:
        try:
            body = r.json()
        except json.JSONDecodeError:
            return CheckResult(path, 200, False, "non-JSON body")

        expected = EXPECTED_FIELDS.get(path, [])
        # The list endpoint has a 0-len fallback; the level path uses parameter substitution
        if "level/" in path:
            expected = EXPECTED_FIELDS.get("/api/bootcamp/level/2", [])

        missing = [f for f in expected if f not in body]
        if missing:
            return CheckResult(path, 200, False, f"missing fields: {missing}")
        return CheckResult(path, 200, True, "OK")

    # 404 / 425 are graceful empty-state responses
    return CheckResult(
        path, r.status_code, True,
        {404: "no games yet (graceful)", 425: "analysis pending (graceful)"}[r.status_code],
    )


def needs_replay_id_lookup(session: requests.Session, base_url: str) -> Optional[int]:
    """Get a real replay ID for the /api/replays/{id} test, if one exists."""
    url = base_url.rstrip("/") + "/api/replays?limit=1"
    try:
        r = session.get(url, timeout=10)
    except requests.RequestException:
        return None
    if r.status_code != 200:
        return None
    try:
        body = r.json()
    except json.JSONDecodeError:
        return None
    items = body.get("replays") or []
    if items:
        return items[0].get("game_replay_id")
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Phase 4 analytics-API smoke test")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("SMOKE_BASE_URL", "http://localhost:8000"),
        help="Base URL of the running server (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--cookie",
        default=os.environ.get("SMOKE_COOKIE", ""),
        help="Cookie header value for authenticated requests "
             "(e.g. 'session=...; guest_token=...')",
    )
    parser.add_argument(
        "--header",
        action="append",
        default=[],
        help="Extra header(s) to send, format 'Key: Value' (repeatable)",
    )
    args = parser.parse_args()

    session = requests.Session()
    if args.cookie:
        session.headers["Cookie"] = args.cookie
    for h in args.header:
        if ":" in h:
            k, v = h.split(":", 1)
            session.headers[k.strip()] = v.strip()

    # Build the checklist. Order matters: discover a replay ID via /api/replays
    # before testing /api/replays/{id}.
    checks = [
        ("/api/bootcamp/diagnosis",  {"difficulty": "expert"}),
        ("/api/bootcamp/level/2",    {"difficulty": "expert"}),
        ("/api/radar",               {"difficulty": "expert", "mode": "standard"}),
        ("/api/patterns/fluency",    {"difficulty": "expert"}),
        ("/api/replays",             {"limit": 5}),
        ("/api/heatmap",             {"difficulty": "expert", "time_range_days": 30}),
    ]

    results: list[CheckResult] = []
    for path, params in checks:
        results.append(run_check(session, args.base_url, path, params))

    # Pick up a replay_id and test the parameterized endpoint
    replay_id = needs_replay_id_lookup(session, args.base_url)
    if replay_id is not None:
        replay_path = f"/api/replays/{replay_id}"
        results.append(run_check(session, args.base_url, replay_path))
    else:
        results.append(CheckResult(
            "/api/replays/<id>", 0, True,
            "skipped (no replays in account yet — graceful)",
        ))

    # Report
    print()
    print(f"=== Phase 4 smoke test against {args.base_url} ===")
    print()
    width = max(len(r.endpoint) for r in results) + 2
    failures = 0
    for r in results:
        mark = "✓" if r.ok else "✗"
        status_str = f"{r.status:>3}" if r.status else " — "
        print(f"  [{mark}] {r.endpoint:<{width}} → {status_str}  {r.note}")
        if not r.ok:
            failures += 1
    print()

    if failures == 0:
        print(f"PASS — all {len(results)} endpoints responded sensibly.")
        return 0
    print(f"FAIL — {failures} of {len(results)} endpoints had problems.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
