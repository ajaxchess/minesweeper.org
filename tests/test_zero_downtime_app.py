"""
tests/test_zero_downtime_app.py — the app side of F-ZERO-DOWNTIME and the rules in
scripts/zero_downtime/deploy_tools.py. The deploy script itself is exercised end to
end in tests/test_zero_downtime_deploy.py.
"""
import base64
import importlib.util
import json
import os
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from conftest import ROOT

_spec = importlib.util.spec_from_file_location(
    "deploy_tools", Path(ROOT) / "scripts" / "zero_downtime" / "deploy_tools.py")
deploy_tools = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(deploy_tools)


# ── PvP: restart unless clearly unrelated ─────────────────────────────────────

def _tree(root: Path, files: dict) -> Path:
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
    return root


PVP_TREE = {
    "duel_routes.py": 'return templates.TemplateResponse(request, "duel.html", {})\n',
    "pvp_leaderboard_routes.py": 'TemplateResponse(request, "pvp_rankings.html")\n',
    "templates/base.html": ('{% include "partials/nav.html" %}\n'
                            '<script src="/static/js/minesweeper.js?v=12" defer></script>\n'
                            '<link rel="stylesheet" href="/static/css/style.css">\n'),
    "templates/partials/nav.html": "<nav></nav>\n",
    "templates/duel.html": '{% extends "base.html" %}\n<script src="/static/js/duel.js"></script>\n',
    "templates/pvp_rankings.html": '{% extends "base.html" %}\n',
    "templates/sudoku.html": '{% extends "base.html" %}\n<script src="/static/js/sudoku.js"></script>\n',
    "static/js/duel.js": 'import("/static/js/duel_chat.js");\n',
}


@pytest.fixture
def tree(tmp_path):
    return _tree(tmp_path / "t", PVP_TREE)


@pytest.mark.parametrize("changed", [
    [], ["docs/x.md"], ["intent/X.md", "tests/test_x.py"], ["BUGS.md"], ["mobile/msmobile/App.js"],
    ["scripts/zero_downtime/deploy.sh"], ["sudoku_routes.py", "sudoku_grader.py"],
    ["templates/sudoku.html"], ["static/src/js/sudoku.js", "static/js/sudoku.js"],
    ["phase7_drills/routes.py"],
])
def test_unrelated_changes_leave_pvp_alone(tree, changed):
    assert deploy_tools.pvp_restart_reason(changed, tree, tree) is None


@pytest.mark.parametrize("changed, why", [
    (["main.py"], "main.py"),
    (["translations.py"], "translations.py"),
    (["requirements.lock"], "requirements.lock"),
    (["database_template.py"], "database_template.py"),
    (["duel.py"], "duel.py"),
    (["game_catalog.py"], "game_catalog.py"),          # template global: feeds the nav
    (["templates/base.html"], "templates/base.html"),
    (["templates/partials/nav.html"], "nav.html"),      # included by base.html
    (["templates/pvp_rankings.html"], "pvp_rankings"),
    (["static/src/js/minesweeper.js"], "minesweeper.js"),
    (["static/css/style.css"], "style.css"),
    (["static/js/duel_chat.js"], "duel_chat.js"),       # loaded by duel.js
    (["brand_new_module.py"], "brand_new_module.py"),   # unknown → restart
    (["docs/x.md", "main.py"], "main.py"),              # one relevant file is enough
])
def test_changes_pvp_uses_restart_it(tree, changed, why):
    reason = deploy_tools.pvp_restart_reason(changed, tree, tree)
    assert reason and why in reason


def test_template_dropped_from_pvp_still_counts(tmp_path):
    """The old tree is what PvP runs now: a template it used counts even if the new
    commit no longer uses it."""
    old = _tree(tmp_path / "old", PVP_TREE)
    new = _tree(tmp_path / "new", {**PVP_TREE, "templates/duel.html": '{% extends "base.html" %}\n'})
    assert deploy_tools.pvp_restart_reason(["static/js/duel.js"], old, new)
    assert deploy_tools.pvp_restart_reason(["static/js/duel.js"], new, new) is None


def test_real_repository_pvp_files():
    repo = Path(ROOT)
    templates = deploy_tools.pvp_templates(repo)
    assert {"templates/base.html", "templates/duel.html", "templates/spectate.html"} <= templates
    static = deploy_tools.pvp_static_files(repo, templates)
    assert {"static/src/js/minesweeper.js", "static/src/js/duel.js", "static/src/css/style.css"} <= static
    assert deploy_tools.pvp_restart_reason(["templates/sudoku.html"], repo, repo) is None
    assert deploy_tools.pvp_restart_reason(["main.py"], repo, repo)


def test_pvp_affected_command_exit_codes(tree):
    tool = str(Path(ROOT) / "scripts" / "zero_downtime" / "deploy_tools.py")
    run = lambda changed: subprocess.run(
        [sys.executable, tool, "pvp-affected", "--old-tree", str(tree), "--new-tree", str(tree)],
        input=changed, capture_output=True, text=True)
    skip = run("docs/a.md\n")
    assert skip.returncode == 10 and skip.stdout.startswith("skip")
    restart = run("docs/a.md\nmain.py\n")
    assert restart.returncode == 0 and "main.py" in restart.stdout


# ── Automatic rollback threshold ──────────────────────────────────────────────

T0 = datetime(2026, 11, 15, 10, 0, 0, tzinfo=timezone.utc)


def _line(path="/", status=200, at=T0 + timedelta(seconds=10), method="GET"):
    ts = at.strftime("%d/%b/%Y:%H:%M:%S %z")
    return f'203.0.113.9 - - [{ts}] "{method} {path} HTTP/1.1" {status} 512 "-" "Mozilla/5.0" 12345\n'


def _verdict(lines):
    return deploy_tools.verdict(lines, T0.timestamp(), (T0 + timedelta(minutes=5)).timestamp())


def test_five_errors_over_two_percent_rolls_back():
    v = _verdict([_line()] * 95 + [_line(status=500)] * 5)
    assert v == {"total": 100, "errors": 5, "share": 0.05, "rollback": True}


def test_four_errors_never_roll_back():
    """The minimum count stops a quiet night's stray errors from triggering it."""
    assert not _verdict([_line()] * 10 + [_line(status=502)] * 4)["rollback"]


def test_five_errors_at_two_percent_or_less_do_not_roll_back():
    assert not _verdict([_line()] * 245 + [_line(status=503)] * 5)["rollback"]     # 2.0%


def test_only_website_requests_in_the_window_count():
    lines = (
        [_line(status=500, path=p) for p in ("/ws/abc", "/duel", "/duelold", "/pvp/bot", "/pvpbeta")] * 2
        + [_line(status=500, path="/static/js/x.js")] * 5
        + [_line(status=500, at=T0 - timedelta(seconds=1))] * 5        # before the switch
        + [_line(status=500, at=T0 + timedelta(minutes=6))] * 5        # after the window
        + ["garbage\n", "==> access.log <==\n", '1.2.3.4 - - [bad date] "GET / HTTP/1.1" 500 1 "-" "-" 1\n']
        + [_line()] * 3
    )
    v = _verdict(lines)
    assert (v["total"], v["errors"], v["rollback"]) == (3, 0, False)


def test_post_errors_count_too():
    v = _verdict([_line(method="POST", path="/api/scores", status=500)] * 6)
    assert v["rollback"] and v["errors"] == 6


def test_watch_verdict_command(tmp_path):
    tool = str(Path(ROOT) / "scripts" / "zero_downtime" / "deploy_tools.py")
    out = subprocess.run(
        [sys.executable, tool, "watch-verdict", "--since", str(T0.timestamp()),
         "--until", str((T0 + timedelta(minutes=5)).timestamp())],
        input="".join([_line(status=500)] * 5), capture_output=True, text=True, check=True)
    assert json.loads(out.stdout)["rollback"] is True


# ── The /admin banner ─────────────────────────────────────────────────────────

def test_alert_round_trip(tmp_path, monkeypatch):
    import admin_routes
    path = tmp_path / "state" / "alert.json"
    log = tmp_path / "run.log"
    log.write_text("".join(f"line {i}\n" for i in range(100)))
    deploy_tools.write_alert(path, "rolled_back", "Errors after the switch.", "a" * 40, "b" * 40, log,
                             now=datetime(2026, 11, 15, 10, 5, tzinfo=timezone.utc))
    monkeypatch.setattr(admin_routes, "DEPLOY_ALERT_PATH", str(path))
    alert = admin_routes.read_deploy_alert()
    assert alert["kind"] == "rolled_back" and alert["time"] == "2026-11-15 10:05 UTC"
    assert alert["commit"] == "a" * 40 and alert["serving"] == "b" * 40
    assert alert["log"] == [f"line {i}" for i in range(60, 100)]
    assert not list(path.parent.glob(".deploy_alert.*"))            # no temp files left


def test_missing_or_bad_alert_file(tmp_path, monkeypatch):
    import admin_routes
    monkeypatch.setattr(admin_routes, "DEPLOY_ALERT_PATH", str(tmp_path / "none.json"))
    assert admin_routes.read_deploy_alert() is None
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    monkeypatch.setattr(admin_routes, "DEPLOY_ALERT_PATH", str(bad))
    assert "could not be read" in admin_routes.read_deploy_alert()["reason"]
    bad.write_text("[1, 2]")
    assert "expected format" in admin_routes.read_deploy_alert()["reason"]


def _user(email: str) -> dict:
    """Same shape as auth.set_session_user."""
    return {"user": {"name": "Test", "email": email, "picture": "", "display_name": "Test"}}


def _session_cookie(data: dict) -> str:
    """A cookie Starlette's SessionMiddleware accepts (signed with the test SECRET_KEY)."""
    from itsdangerous import TimestampSigner
    from auth import SECRET_KEY
    payload = base64.b64encode(json.dumps(data).encode())
    return TimestampSigner(str(SECRET_KEY)).sign(payload).decode()


@pytest.fixture
def admin_session(monkeypatch):
    import admin_routes
    monkeypatch.setattr(admin_routes, "ADMIN_EMAILS", {"boss@example.com"})
    return {"session": _session_cookie(_user("boss@example.com"))}


def test_banner_shows_and_dismisses(client, tmp_path, monkeypatch, admin_session):
    import admin_routes
    path = tmp_path / "minesweeper_deploy_alert.json"
    monkeypatch.setattr(admin_routes, "DEPLOY_ALERT_PATH", str(path))

    r = client.get("/admin", cookies=admin_session)
    assert r.status_code == 200, r.text[:300]
    assert "Deploy problem" not in r.text

    deploy_tools.write_alert(path, "health_check_failed", "<b>did not pass</b> its health check", "c" * 40, "d" * 40)
    r = client.get("/admin", cookies=admin_session)
    assert "Deploy problem: health check failed" in r.text
    assert "&lt;b&gt;did not pass&lt;/b&gt;" in r.text                 # escaped
    assert "cccccccc" in r.text and "dddddddd" in r.text

    r = client.post("/admin/deploy-alert/dismiss", cookies=admin_session, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    assert not path.exists()
    assert json.loads((tmp_path / "minesweeper_deploy_alert.dismissed.json").read_text())["kind"] == "health_check_failed"
    assert "Deploy problem" not in client.get("/admin", cookies=admin_session).text


def test_dismiss_requires_an_admin(client, tmp_path, monkeypatch):
    import admin_routes
    path = tmp_path / "alert.json"
    path.write_text('{"reason": "x"}')
    monkeypatch.setattr(admin_routes, "DEPLOY_ALERT_PATH", str(path))
    monkeypatch.setattr(admin_routes, "ADMIN_EMAILS", {"boss@example.com"})
    outsider = {"session": _session_cookie(_user("player@example.com"))}
    for cookies in ({}, outsider):
        r = client.post("/admin/deploy-alert/dismiss", cookies=cookies, follow_redirects=False)
        assert r.status_code == 403
    assert path.exists()


# ── Scheduler: retried lock, never in PvP ─────────────────────────────────────

def test_lock_waiter_starts_the_scheduler_once_the_lock_frees():
    import main
    attempts = iter([False, False, True])
    started = []
    assert main._wait_for_scheduler_lock(threading.Event(), lambda: next(attempts), lambda: started.append(1), 0.001)
    assert started == [1]


def test_lock_waiter_stops_on_shutdown():
    import main
    stop = threading.Event()
    stop.set()
    started = []
    assert not main._wait_for_scheduler_lock(stop, lambda: True, lambda: started.append(1), 0.001)
    assert started == []


def test_startup_retries_when_another_process_holds_the_lock(monkeypatch):
    import main
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "_migrate_numbers_match_puzzle_date", lambda: None)
    monkeypatch.setattr(main, "_SCHEDULER_ENABLED", True)
    monkeypatch.setattr(main, "SCHEDULER_LOCK_RETRY_SECS", 0.01)
    monkeypatch.setattr(main, "_scheduler_waiter_stop", threading.Event())
    attempts = iter([False, False, True])
    monkeypatch.setattr(main, "_acquire_scheduler_lock", lambda: next(attempts, False))
    started = threading.Event()
    monkeypatch.setattr(main, "_start_scheduler", started.set)
    main.startup()
    assert started.wait(2), "the waiting worker never started the scheduler"


def test_scheduler_off_never_takes_the_lock(monkeypatch):
    import main
    monkeypatch.setattr(main, "init_db", lambda: None)
    monkeypatch.setattr(main, "_migrate_numbers_match_puzzle_date", lambda: None)
    monkeypatch.setattr(main, "_SCHEDULER_ENABLED", False)
    called = []
    monkeypatch.setattr(main, "_acquire_scheduler_lock", lambda: called.append(1) or True)
    monkeypatch.setattr(main, "_start_scheduler", lambda: called.append(2))
    main.startup()
    assert called == []


@pytest.mark.parametrize("value, enabled", [("off", False), (" OFF ", False), ("0", False), ("false", False),
                                            ("no", False), ("on", True), ("", True), ("yes", True)])
def test_scheduler_switch_values(value, enabled):
    import main
    assert main._switch_on(value) is enabled


# ── Uploads folder ────────────────────────────────────────────────────────────

def test_upload_folder_defaults_to_static_uploads():
    import settings
    assert settings.upload_dir("jigsaw") == os.path.join("static", "uploads", "jigsaw")


def test_upload_folder_follows_the_environment(tmp_path):
    code = "import settings, jigsaw_routes; print(settings.upload_dir('15puzzle')); print(jigsaw_routes._JIGSAW_UPLOAD_DIR)"
    out = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0, '.');" + code], cwd=ROOT,
                         capture_output=True, text=True, env={**os.environ, "MINESWEEPER_UPLOADS_DIR": str(tmp_path)})
    if out.returncode != 0 and "No module named" in out.stderr:
        pytest.skip("app dependencies not importable outside pytest")
    assert out.stdout.split() == [str(tmp_path / "15puzzle"), str(tmp_path / "jigsaw")]


def test_no_upload_path_is_hardcoded():
    for name in ("admin_routes.py", "fifteen_puzzle_routes.py", "jigsaw_routes.py"):
        assert '"static", "uploads"' not in Path(ROOT, name).read_text(), name
