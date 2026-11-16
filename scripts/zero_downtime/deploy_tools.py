#!/usr/bin/env python3
"""
deploy_tools.py — decisions for the blue/green deploy (F-ZERO-DOWNTIME).

Called by deploy.sh. Standard library only, so it runs with the system python3
even when a copy's virtualenv is broken.

    pvp-affected   Does a deploy need to restart PvP? Changed files on stdin.
                   Exit 0 = restart, 10 = PvP not affected. Anything else is an
                   error, and deploy.sh then restarts PvP to be safe.
    watch-verdict  Roll back? Apache access-log lines on stdin; prints JSON.
    write-alert    Write the /admin deploy banner (admin_routes.read_deploy_alert).

See intent/ZeroDowntimeDeploy.md, decisions 4, 5 and 7.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

EXIT_RESTART = 0
EXIT_SKIP = 10

# ── pvp-affected ──────────────────────────────────────────────────────────────
# "Restart unless clearly unrelated". These are the only paths a deploy may change
# without restarting PvP. Everything not listed here restarts it: main.py,
# translations.py, database_template.py, requirements.lock, settings, auth, …
UNRELATED_DIRS = (
    ".github/", "docs/", "intent/", "tests/", "mobile/", "scripts/", "terraform/",
    "python_prototypes/", "dataanalysis/", "examplescreenshots/", "screenshots/",
    "phase2_analyzer/", "phase4_routes/", "phase5_bootcamp/", "phase7_drills/", "bots/",
)

# Other games' modules. PvP pages never call them, and a running PvP process keeps
# the version it loaded. Shared modules (game_catalog, quest_catalog, blog_routes,
# wc2026_data, …) feed the site nav or template globals, so they are not listed.
UNRELATED_MODULES = frozenset({
    "cylinder_routes.py", "fifteen_puzzle_routes.py", "game2048_routes.py",
    "globesweeper_routes.py", "hexsweeper_routes.py", "jigsaw_routes.py",
    "mahjong_routes.py", "meowdoku_routes.py", "mosaic_routes.py",
    "nonosweeper_routes.py", "numbers_match_routes.py", "numbers_match_engine.py",
    "numbers_match_generator.py", "schulte_routes.py", "speff_routes.py",
    "sudoku_routes.py", "sudoku_generator.py", "sudoku_grader.py",
    "tametsi_routes.py", "tametsi_generator.py", "tentaizu_leaderboard_routes.py",
    "wc2026_routes.py", "wc2026_board.py", "minesweeper_engine.py",
    "score_verification.py", "leaderboard_platform.py", "seo_checker.py",
    "connect_four.py", "gen_flags.py", "download_country_flags.py",
})

# Modules Apache routes PvP traffic to; the templates they render are where the
# PvP template set starts.
PVP_MODULES = ("duel_routes.py", "duelold_routes.py", "pvp_leaderboard_routes.py")

_TEMPLATE_NAME = re.compile(r'["\']([\w./-]+\.html)["\']')
_TEMPLATE_REF = re.compile(r'{%-?\s*(?:extends|include|import|from)\s+["\']([\w./-]+)["\']')
_STATIC_REF = re.compile(r'/static/([\w./-]+?\.\w+)(?=[?"\'\s#)])')


def pvp_templates(tree: Path) -> set[str]:
    """Every template a PvP page uses in this checkout: the ones PvP modules
    render, and everything they extend, include or import, transitively."""
    todo: list[str] = []
    for module in PVP_MODULES:
        path = tree / module
        if path.is_file():
            todo += _TEMPLATE_NAME.findall(path.read_text(encoding="utf-8", errors="replace"))
    seen: set[str] = set()
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        path = tree / "templates" / name
        if path.is_file():
            todo += _TEMPLATE_REF.findall(path.read_text(encoding="utf-8", errors="replace"))
    return {f"templates/{name}" for name in seen}


def pvp_static_files(tree: Path, templates: set[str]) -> set[str]:
    """Static files PvP pages load, as repo paths. Built files in static/js and
    static/css also count through their sources in static/src/."""
    refs: set[str] = set()
    for template in templates:
        path = tree / template
        if path.is_file():
            refs |= set(_STATIC_REF.findall(path.read_text(encoding="utf-8", errors="replace")))
    # One level further: scripts that reference other static files.
    for ref in list(refs):
        path = tree / "static" / ref
        if path.suffix in (".js", ".css") and path.is_file():
            refs |= set(_STATIC_REF.findall(path.read_text(encoding="utf-8", errors="replace")))
    files = {f"static/{ref}" for ref in refs}
    for ref in refs:
        kind, _, rest = ref.partition("/")
        if kind in ("js", "css") and rest:
            files.add(f"static/src/{kind}/{rest}")
    return files


def pvp_restart_reason(changed: list[str], old_tree: Path, new_tree: Path) -> str | None:
    """Why PvP must restart, or None when every changed file is clearly unrelated.
    The old tree is the commit PvP runs now, the new tree the deploy target."""
    templates = pvp_templates(old_tree) | pvp_templates(new_tree)
    static = pvp_static_files(old_tree, pvp_templates(old_tree)) | pvp_static_files(new_tree, pvp_templates(new_tree))
    for path in changed:
        path = path.strip()
        if not path:
            continue
        if path.startswith(UNRELATED_DIRS):
            continue
        if "/" not in path and (path in UNRELATED_MODULES or path.endswith(".md")):
            continue
        if path.startswith("templates/"):
            if path in templates:
                return f"{path} is used by PvP pages"
            continue
        if path.startswith("static/"):
            if path in static:
                return f"{path} is loaded by PvP pages"
            continue
        return f"{path} may affect PvP"
    return None


# ── watch-verdict ─────────────────────────────────────────────────────────────
# Same prefixes Apache sends to the PvP service; those requests are not counted.
PVP_PATH_PREFIXES = ("/ws/", "/duel", "/pvp")
MIN_ERRORS = 5
MAX_ERROR_SHARE = 0.02

# combined_timing: %h %l %u %t "%r" %>s %O "%{Referer}i" "%{User-Agent}i" %D
_LOG_LINE = re.compile(r'^\S+ \S+ \S+ \[(?P<ts>[^\]]+)\] "(?P<req>[^"]*)" (?P<status>\d{3}) ')


def website_responses(lines, since: float, until: float):
    """(path, status) of every website request Apache logged in [since, until]."""
    for line in lines:
        m = _LOG_LINE.match(line)
        if not m:
            continue
        try:
            ts = datetime.strptime(m["ts"], "%d/%b/%Y:%H:%M:%S %z").timestamp()
        except ValueError:
            continue
        if not since <= ts <= until:
            continue
        parts = m["req"].split()
        path = parts[1] if len(parts) > 1 else ""
        if path.startswith("/static/") or path.startswith(PVP_PATH_PREFIXES):
            continue
        yield path, int(m["status"])


def verdict(lines, since: float, until: float) -> dict:
    """Roll back when at least MIN_ERRORS website responses are 5xx and they are
    more than MAX_ERROR_SHARE of website requests in the window."""
    total = errors = 0
    for _, status in website_responses(lines, since, until):
        total += 1
        errors += status >= 500
    share = errors / total if total else 0.0
    return {
        "total": total,
        "errors": errors,
        "share": round(share, 4),
        "rollback": errors >= MIN_ERRORS and share > MAX_ERROR_SHARE,
    }


# ── write-alert ───────────────────────────────────────────────────────────────
LOG_LINES_IN_ALERT = 40


def write_alert(path: Path, kind: str, reason: str, commit: str = "", serving: str = "",
                log_file: Path | None = None, now: datetime | None = None) -> dict:
    """Write the banner record atomically, so /admin never reads half a file."""
    log: list[str] = []
    if log_file and log_file.is_file():
        log = log_file.read_text(encoding="utf-8", errors="replace").splitlines()[-LOG_LINES_IN_ALERT:]
    alert = {
        "time": (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC"),
        "kind": kind,
        "reason": reason,
        "commit": commit,
        "serving": serving,
        "log": log,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".deploy_alert.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(alert, fh, indent=2)
        os.chmod(tmp, 0o644)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return alert


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("pvp-affected")
    p.add_argument("--old-tree", type=Path, required=True, help="checkout PvP runs now")
    p.add_argument("--new-tree", type=Path, required=True, help="checkout of the deploy target")

    w = sub.add_parser("watch-verdict")
    w.add_argument("--since", type=float, required=True, help="Unix time of the switch")
    w.add_argument("--until", type=float, default=None, help="end of the window (default: now)")

    a = sub.add_parser("write-alert")
    a.add_argument("--path", type=Path, required=True)
    a.add_argument("--kind", required=True)
    a.add_argument("--reason", required=True)
    a.add_argument("--commit", default="")
    a.add_argument("--serving", default="")
    a.add_argument("--log-file", type=Path, default=None)

    args = parser.parse_args(argv)
    if args.command == "pvp-affected":
        reason = pvp_restart_reason(sys.stdin.read().splitlines(), args.old_tree, args.new_tree)
        print(f"restart: {reason}" if reason else "skip: every changed file is unrelated to PvP")
        return EXIT_RESTART if reason else EXIT_SKIP
    if args.command == "watch-verdict":
        until = args.until if args.until is not None else datetime.now(timezone.utc).timestamp()
        print(json.dumps(verdict(sys.stdin, args.since, until)))
        return 0
    write_alert(args.path, args.kind, args.reason, args.commit, args.serving, args.log_file)
    return 0


if __name__ == "__main__":
    sys.exit(main())
