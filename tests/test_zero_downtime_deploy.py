"""
tests/test_zero_downtime_deploy.py — runs scripts/zero_downtime/deploy.sh end to end
(F-ZERO-DOWNTIME).

The real script runs against a temporary layout: three git worktrees (blue, green,
pvp), the live symlink, the shared folder and the deploy-state files. Stand-ins
replace what only exists on the server:
  * systemctl starts and stops tiny HTTP servers that answer /health with the
    commit checked out in their copy, and the smoke-test pages;
  * sudo just runs the command;
  * flock and `mv -T` are provided where the system lacks them (macOS).
A copy containing a file named BROKEN answers 500; a copy containing
ERRORS_AFTER_SWITCH makes the old copy's stop write 5xx lines to the access log,
as if the new code failed under real traffic.
"""
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import pytest

from conftest import ROOT

DEPLOY_SH = Path(ROOT) / "scripts" / "zero_downtime" / "deploy.sh"
CATCHUP_SH = Path(ROOT) / "scripts" / "zero_downtime" / "pvp_catchup.sh"


def _bash5():
    for candidate in (shutil.which("bash"), "/opt/homebrew/bin/bash", "/usr/local/bin/bash", "/bin/bash"):
        if not candidate or not os.path.exists(candidate):
            continue
        out = subprocess.run([candidate, "-c", "echo ${BASH_VERSINFO[0]}"], capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip().isdigit() and int(out.stdout.strip()) >= 4:
            return candidate
    return None


BASH = _bash5()
pytestmark = pytest.mark.skipif(
    not (BASH and shutil.which("git") and shutil.which("curl")),
    reason="needs bash 4+, git and curl",
)

FAKE_APP = textwrap.dedent('''
    import json, os, subprocess, sys
    from http.server import BaseHTTPRequestHandler, HTTPServer
    copy, port = sys.argv[1], int(sys.argv[2])
    PAGES = {"/": "minesweeper", "/tentaizu": "Tentaizu", "/numbers-match": "Numbers Match"}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def _send(self, code, body, ctype="text/html"):
            data = body.encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def do_GET(self):
            if self.path == "/health":
                head = subprocess.run(["git", "-C", copy, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
                return self._send(200, json.dumps({"status": "ok", "commit": head}), "application/json")
            if os.path.exists(os.path.join(copy, "BROKEN")):
                return self._send(500, "Internal Server Error")
            if self.path.startswith("/api/numbers-match-board/"):
                return self._send(200, json.dumps({"board_data": []}), "application/json")
            if self.path in PAGES:
                return self._send(200, f"<html>{PAGES[self.path]}</html>")
            return self._send(404, "not found")

    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
''')

FAKE_SYSTEMCTL = textwrap.dedent('''
    import os, signal, socket, subprocess, sys, time
    from datetime import datetime, timezone
    state = os.environ["FAKE_SYSTEMD_DIR"]
    base = os.environ["MS_ZD_BASE"]
    args = [a for a in sys.argv[1:] if not a.startswith("--quiet") and a != "--runtime"]
    with open(os.path.join(state, "calls.log"), "a") as fh:
        fh.write(" ".join(args) + "\\n")
    action, units = args[0], args[1:]

    def where(unit):
        if unit == "minesweeper-pvp":
            return os.path.join(base, "minesweeper-pvp"), int(os.environ["MS_ZD_PVP_PORT"])
        color = unit.split("@", 1)[1]
        return os.path.join(base, f"minesweeper-{color}"), int(os.environ[f"MS_ZD_{color.upper()}_PORT"])

    def pidfile(unit):
        return os.path.join(state, unit + ".pid")

    def running(unit):
        try:
            pid = int(open(pidfile(unit)).read())
            os.kill(pid, 0)
            return pid
        except (OSError, ValueError):
            return None

    def start(unit):
        if running(unit):
            return
        copy, port = where(unit)
        proc = subprocess.Popen([sys.executable, os.environ["FAKE_APP"], copy, str(port)],
                                start_new_session=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        open(pidfile(unit), "w").write(str(proc.pid))
        for _ in range(100):
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.1).close()
                return
            except OSError:
                time.sleep(0.05)
        sys.exit("fake app did not start")

    def stop(unit):
        pid = running(unit)
        if pid:
            os.kill(pid, signal.SIGTERM)
            for _ in range(100):
                try:
                    os.kill(pid, 0)
                    time.sleep(0.02)
                except OSError:
                    break
        if os.path.exists(pidfile(unit)):
            os.remove(pidfile(unit))
        # Simulate the new copy failing under real traffic once the old one is gone.
        if unit.startswith("minesweeper-web@"):
            other = "green" if unit.endswith("blue") else "blue"
            if os.path.exists(os.path.join(base, f"minesweeper-{other}", "ERRORS_AFTER_SWITCH")):
                ts = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S +0000")
                with open(os.environ["MS_ZD_APACHE_LOG"], "a") as log:
                    for _ in range(20):
                        log.write(f'1.2.3.4 - - [{ts}] "GET / HTTP/1.1" 500 10 "-" "test" 1000\\n')

    for unit in units:
        if action == "start":
            start(unit)
        elif action == "stop":
            stop(unit)
        elif action == "restart":
            stop(unit); start(unit)
    sys.exit(0)
''')


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


class Layout:
    """A production-shaped layout in a temp dir, with blue live and PvP running."""

    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.base = tmp / "base"
        self.shims = tmp / "shims"
        self.systemd = tmp / "systemd"
        self.access_log = tmp / "access.log"
        for d in (self.base, self.shims, self.systemd, self.base / "deploy_state",
                  self.base / "minesweeper-shared"):
            d.mkdir(parents=True, exist_ok=True)
        self.access_log.write_text("")
        (self.base / "minesweeper-shared" / ".env").write_text("DB_USER=u\nDB_PASS='p/&\\x'\nDB_NAME=n\n")
        self._write_shims()

        # Repository: origin (bare) and the checkout the worktrees hang off.
        self.origin = tmp / "origin.git"
        self.src = tmp / "src"
        subprocess.run(["git", "init", "--bare", "-q", str(self.origin)], check=True)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.src)], check=True)
        _git(self.src, "config", "user.email", "t@example.com")
        _git(self.src, "config", "user.name", "Test")
        _git(self.src, "remote", "add", "origin", str(self.origin))
        files = {
            "main.py": "app = None\n",
            "database_template.py": 'USER = "the_minesweeper_user"\nPW = "the_password"\nDB = "the_db_name"\n',
            "requirements.lock": "fastapi==1\n",
            "duel_routes.py": 'TEMPLATE = "duel.html"\n',
            "templates/base.html": '<script src="/static/js/minesweeper.js?v=1"></script>\n',
            "templates/duel.html": '{% extends "base.html" %}\n',
            "templates/sudoku.html": "sudoku\n",
            "docs/notes.md": "notes\n",
        }
        for name, text in files.items():
            path = self.src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        self.commit_a = self.commit("A: first release")
        for name in ("blue", "green", "pvp"):
            copy = self.copy(name)
            _git(self.src, "worktree", "add", "-q", "--detach", str(copy), self.commit_a)
            pip = copy / "venv" / "bin" / "pip"
            pip.parent.mkdir(parents=True)
            pip.write_text("#!/bin/sh\nexit 0\n")
            pip.chmod(0o755)
        (self.base / "minesweeper").symlink_to("minesweeper-blue")
        self.set_last_good(self.commit_a)

        self.env = {
            **os.environ,
            "PATH": f"{self.shims}:{os.environ['PATH']}",
            "MS_ZD_BASE": str(self.base),
            "MS_ZD_LOCK": str(tmp / "deploy.lock"),
            "MS_ZD_APACHE_LOG": str(self.access_log),
            "MS_ZD_BLUE_PORT": str(_free_port()),
            "MS_ZD_GREEN_PORT": str(_free_port()),
            "MS_ZD_PVP_PORT": str(_free_port()),
            "MS_ZD_HEALTH_TIMEOUT": "6",
            "MS_ZD_WATCH_SECONDS": "2",
            "MS_ZD_WATCH_INTERVAL": "1",
            "MS_ZD_SETTLE_SECONDS": "0",
            "FAKE_SYSTEMD_DIR": str(self.systemd),
            "FAKE_APP": str(tmp / "fake_app.py"),
        }
        self.systemctl("start", "minesweeper-web@blue", "minesweeper-pvp")

    # ── helpers ──
    def _write_shims(self):
        (self.tmp / "fake_app.py").write_text(FAKE_APP)
        shims = {
            "systemctl": f"#!{sys.executable}\n{FAKE_SYSTEMCTL}",
            "sudo": '#!/bin/sh\n[ "$1" = "-n" ] && shift\nexec "$@"\n',
        }
        if not shutil.which("flock"):
            shims["flock"] = (f"#!{sys.executable}\nimport fcntl, sys\n"
                              "try:\n    fcntl.flock(int(sys.argv[-1]), fcntl.LOCK_EX | fcntl.LOCK_NB)\n"
                              "except OSError:\n    sys.exit(1)\n")
        if subprocess.run(["mv", "--version"], capture_output=True).returncode != 0:   # BSD mv: no -T
            shims["mv"] = (f"#!{sys.executable}\nimport os, sys\n"
                           "args = [a for a in sys.argv[1:] if not a.startswith('-')]\n"
                           "if any(a.startswith('-') and 'T' in a for a in sys.argv[1:]):\n"
                           "    os.replace(args[0], args[1])\nelse:\n    os.execv('/bin/mv', ['mv'] + sys.argv[1:])\n")
        for name, text in shims.items():
            path = self.shims / name
            path.write_text(text)
            path.chmod(0o755)

    def systemctl(self, *args):
        subprocess.run([str(self.shims / "systemctl"), *args], check=True,
                       env={**os.environ, **getattr(self, "env", {}), "MS_ZD_BASE": str(self.base)})

    def copy(self, name):
        return self.base / f"minesweeper-{name}"

    def commit(self, message, changes=None):
        for name, text in (changes or {}).items():
            path = self.src / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
        _git(self.src, "add", "-A")
        _git(self.src, "commit", "-q", "-m", message)
        sha = _git(self.src, "rev-parse", "HEAD")
        _git(self.src, "push", "-q", "origin", "HEAD:main")
        return sha

    def set_last_good(self, sha):
        (self.base / "deploy_state" / "minesweeper_last_good_commit").write_text(sha + "\n")

    def deploy(self, *args):
        result = subprocess.run([BASH, str(DEPLOY_SH), *args], env=self.env, capture_output=True, text=True, timeout=120)
        self.last_output = result.stdout + result.stderr
        return result

    def live(self):
        return os.readlink(self.base / "minesweeper")

    def head(self, name):
        return _git(self.copy(name), "rev-parse", "HEAD")

    def health(self, port_var):
        out = subprocess.run(["curl", "-s", "--max-time", "2", f"http://127.0.0.1:{self.env[port_var]}/health"],
                             capture_output=True, text=True).stdout
        return json.loads(out)["commit"] if out else None

    def blocked(self):
        path = self.base / "deploy_state" / "minesweeper_prod_blocked_commit"
        return path.read_text().strip() if path.exists() else None

    def alert(self):
        path = self.base / "deploy_state" / "minesweeper_deploy_alert.json"
        return json.loads(path.read_text()) if path.exists() else None

    def calls(self):
        path = self.systemd / "calls.log"
        return path.read_text().splitlines() if path.exists() else []

    def shutdown(self):
        for pidfile in self.systemd.glob("*.pid"):
            try:
                os.kill(int(pidfile.read_text()), signal.SIGTERM)
            except (OSError, ValueError):
                pass


@pytest.fixture
def layout(tmp_path):
    lay = Layout(tmp_path)
    yield lay
    lay.shutdown()


def _calls_since(lay, before):
    return lay.calls()[before:]


# ── Deploys ───────────────────────────────────────────────────────────────────

def test_nothing_to_deploy(layout):
    r = layout.deploy()
    assert r.returncode == 0, layout.last_output
    assert "Nothing to deploy" in layout.last_output
    assert layout.live() == "minesweeper-blue"


def test_deploy_switches_to_the_other_copy_and_leaves_pvp_alone(layout):
    b = layout.commit("B: docs only", {"docs/notes.md": "more notes\n"})
    layout.set_last_good(b)
    before = len(layout.calls())

    r = layout.deploy()

    assert r.returncode == 0, layout.last_output
    assert layout.live() == "minesweeper-green"
    assert layout.health("MS_ZD_GREEN_PORT") == b
    assert layout.health("MS_ZD_BLUE_PORT") is None               # old copy stopped
    calls = _calls_since(layout, before)
    assert calls.index("start minesweeper-web@green") < calls.index("stop minesweeper-web@blue")
    assert "enable minesweeper-web@green" in calls and "disable minesweeper-web@blue" in calls
    # PvP: docs/ is unrelated, so it stays on A and is not touched.
    assert layout.head("pvp") == layout.commit_a
    assert not any("minesweeper-pvp" in c for c in calls)
    assert "PvP left on" in layout.last_output
    # database.py generated from the shared .env, special characters intact.
    db = (layout.copy("green") / "database.py").read_text()
    assert 'USER = "u"' in db and 'PW = "p/&\\x"' in db
    assert layout.blocked() is None and layout.alert() is None


def test_next_deploy_goes_back_to_blue(layout):
    b = layout.commit("B", {"docs/notes.md": "b\n"})
    layout.set_last_good(b)
    assert layout.deploy().returncode == 0
    c = layout.commit("C", {"docs/notes.md": "c\n"})
    layout.set_last_good(c)

    assert layout.deploy().returncode == 0, layout.last_output
    assert layout.live() == "minesweeper-blue"
    assert layout.health("MS_ZD_BLUE_PORT") == c
    assert layout.head("green") == b                                # previous release kept for rollback


def test_deploy_that_affects_pvp_restarts_it(layout):
    b = layout.commit("B: shared code", {"main.py": "app = 'b'\n"})
    layout.set_last_good(b)

    assert layout.deploy().returncode == 0, layout.last_output
    assert layout.head("pvp") == b
    assert layout.health("MS_ZD_PVP_PORT") == b
    assert "restart: main.py may affect PvP" in layout.last_output


def test_pvp_template_change_restarts_pvp_but_other_templates_do_not(layout):
    b = layout.commit("B: sudoku page", {"templates/sudoku.html": "new sudoku\n"})
    layout.set_last_good(b)
    assert layout.deploy().returncode == 0
    assert layout.head("pvp") == layout.commit_a

    c = layout.commit("C: base template", {"templates/base.html": '<script src="/static/js/minesweeper.js?v=2"></script>\n'})
    layout.set_last_good(c)
    assert layout.deploy().returncode == 0
    assert layout.head("pvp") == c


def test_failed_health_check_never_takes_traffic(layout):
    b = layout.commit("B: broken", {"BROKEN": "x\n"})
    layout.set_last_good(b)

    r = layout.deploy()

    assert r.returncode == 1
    assert layout.live() == "minesweeper-blue"
    assert layout.health("MS_ZD_BLUE_PORT") == layout.commit_a     # still serving
    assert layout.health("MS_ZD_GREEN_PORT") is None               # new copy stopped again
    assert layout.blocked() == b
    alert = layout.alert()
    assert alert["kind"] == "health_check_failed" and alert["commit"] == b
    assert alert["serving"] == layout.commit_a
    assert any("FAIL: Home" in line for line in alert["log"])
    assert layout.head("pvp") == layout.commit_a

    # The blocked commit is not retried on the next cron tick.
    assert layout.deploy().returncode == 0
    assert "is blocked in production" in layout.last_output


def test_errors_after_the_switch_roll_back_automatically(layout):
    b = layout.commit("B: fails under traffic", {"ERRORS_AFTER_SWITCH": "x\n"})
    layout.set_last_good(b)

    r = layout.deploy()

    assert r.returncode == 1, layout.last_output
    assert layout.live() == "minesweeper-blue"
    assert layout.health("MS_ZD_BLUE_PORT") == layout.commit_a
    assert layout.health("MS_ZD_GREEN_PORT") is None
    # The root-level file counted as a PvP change, so PvP was updated and rolled back.
    assert layout.head("pvp") == layout.commit_a
    assert layout.health("MS_ZD_PVP_PORT") == layout.commit_a
    assert layout.blocked() == b
    alert = layout.alert()
    assert alert["kind"] == "rolled_back" and alert["serving"] == layout.commit_a
    assert '"rollback": true' in layout.last_output


def test_force_deploys_origin_main_even_when_blocked(layout):
    b = layout.commit("B: broken", {"BROKEN": "x\n"})
    layout.set_last_good(b)
    layout.deploy()
    _git(layout.src, "rm", "-q", "BROKEN")
    c = layout.commit("C: remove the breakage")

    r = layout.deploy("--force")

    assert r.returncode == 0, layout.last_output
    assert layout.health("MS_ZD_GREEN_PORT") == c
    last_good = (layout.base / "deploy_state" / "minesweeper_last_good_commit").read_text().strip()
    assert last_good == c


# ── Manual rollback ───────────────────────────────────────────────────────────

def test_manual_rollback_refuses_to_go_to_a_blocked_commit(layout):
    """After an automatic rollback the idle copy holds the bad commit."""
    b = layout.commit("B: fails under traffic", {"ERRORS_AFTER_SWITCH": "x\n"})
    layout.set_last_good(b)
    assert layout.deploy().returncode == 1
    assert layout.head("green") == b

    r = layout.deploy("--rollback")

    assert r.returncode == 1
    assert "Refusing" in layout.last_output
    assert layout.live() == "minesweeper-blue"
    assert layout.health("MS_ZD_BLUE_PORT") == layout.commit_a


def test_manual_rollback_returns_to_the_previous_release_and_blocks(layout):
    b = layout.commit("B", {"main.py": "app = 'b'\n"})
    layout.set_last_good(b)
    assert layout.deploy().returncode == 0
    assert layout.head("pvp") == b

    r = layout.deploy("--rollback")

    assert r.returncode == 0, layout.last_output
    assert layout.live() == "minesweeper-blue"
    assert layout.health("MS_ZD_BLUE_PORT") == layout.commit_a
    assert layout.health("MS_ZD_GREEN_PORT") is None
    assert layout.head("pvp") == layout.commit_a                  # PvP followed
    assert layout.blocked() == b
    assert layout.alert()["kind"] == "manual_rollback"
    # The next tick does not redeploy the rolled-back commit.
    assert layout.deploy().returncode == 0
    assert "is blocked in production" in layout.last_output


def test_switch_between_copies_on_the_same_commit_blocks_nothing(layout):
    r = layout.deploy("--rollback")
    assert r.returncode == 0, layout.last_output
    assert layout.live() == "minesweeper-green"
    assert layout.health("MS_ZD_GREEN_PORT") == layout.commit_a
    assert layout.blocked() is None and layout.alert() is None


# ── Status, locking, PvP catch-up ─────────────────────────────────────────────

def test_status_changes_nothing(layout):
    before = len(layout.calls())
    r = layout.deploy("--status")
    assert r.returncode == 0
    assert f"live copy:   blue" in r.stdout and layout.commit_a in r.stdout
    assert len(layout.calls()) == before


def test_a_second_deploy_waits_for_the_first(layout):
    import fcntl
    with open(layout.env["MS_ZD_LOCK"], "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        layout.set_last_good(layout.commit("B", {"docs/notes.md": "b\n"}))
        r = layout.deploy()
    assert r.returncode == 0
    assert "Another deploy is running" in layout.last_output
    assert layout.live() == "minesweeper-blue"


def test_nightly_catchup_brings_pvp_to_the_website_commit(layout):
    b = layout.commit("B: sudoku only", {"templates/sudoku.html": "s\n"})
    layout.set_last_good(b)
    assert layout.deploy().returncode == 0
    assert layout.head("pvp") == layout.commit_a

    r = subprocess.run([BASH, str(CATCHUP_SH)], env=layout.env, capture_output=True, text=True, timeout=60)

    assert r.returncode == 0, r.stdout + r.stderr
    assert layout.head("pvp") == b
    assert layout.health("MS_ZD_PVP_PORT") == b

    r = subprocess.run([BASH, str(CATCHUP_SH)], env=layout.env, capture_output=True, text=True, timeout=60)
    assert "already on" in r.stdout
