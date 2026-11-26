"""
tests/test_score_verification_stats.py — failure reasons are stored and the admin
statistics page counts verified and failed classic scores (F-MS-VERIFY-STATS).
"""
import base64
import json

import pytest

import database as db_module
import ms_games
import settings as site_settings
from conftest import XHR
from database import Score

BARE = {"name": "NoLog", "mode": "beginner", "time_secs": 1, "time_ms": 1,
        "rows": 9, "cols": 9, "mines": 10, "no_guess": False}


def _session_cookie(email: str) -> str:
    from itsdangerous import TimestampSigner
    from auth import SECRET_KEY
    data = {"user": {"name": "Test", "email": email, "picture": "", "display_name": "Test"}}
    return TimestampSigner(str(SECRET_KEY)).sign(base64.b64encode(json.dumps(data).encode())).decode()


@pytest.fixture
def admin(monkeypatch):
    import admin_routes
    monkeypatch.setattr(admin_routes, "ADMIN_EMAILS", {"boss@example.com"})
    return {"session": _session_cookie("boss@example.com")}


@pytest.fixture(autouse=True)
def observe_mode(monkeypatch):
    monkeypatch.setattr(site_settings, "SCORE_VERIFICATION_MODE", "observe")


def stored(name):
    db = db_module.SessionLocal()
    try:
        return db.query(Score).filter(Score.name == name).one()
    finally:
        db.close()


def _submit_mix(client):
    assert ms_games.post(client, name="Good", time_ms=30_000).status_code == 201
    body = {**ms_games.submission(name="Boom", time_ms=31_000, mines=list(range(10, 20))),
            "log": [[0, "l", 1, 1]]}   # (1, 1) is cell 10, a mine
    assert client.post("/api/scores", json=body, headers=XHR).status_code == 201
    assert client.post("/api/scores", json=BARE, headers=XHR).status_code == 201


def test_failure_reason_is_stored(client):
    _submit_mix(client)
    assert stored("Good").verification == "verified" and stored("Good").verification_reason is None
    assert stored("Boom").verification == "failed"
    assert stored("Boom").verification_reason == "a mine was revealed"
    assert stored("NoLog").verification == "unverified"
    assert stored("NoLog").verification_reason == "no game token or move log"


def test_page_counts_verified_and_failed(client, admin):
    _submit_mix(client)
    r = client.get("/admin/score-verification?days=7", cookies=admin)
    assert r.status_code == 200, r.text[:300]
    html = r.text
    assert "Score Verification" in html and "observe" in html
    assert "33.3%" in html                       # 1 verified of 3 checked
    assert "a mine was revealed" in html and "no game token or move log" in html
    assert "Boom" in html and "NoLog" in html    # recent failures list
    assert "Good" not in html.split("Most recent failed")[1]


def test_unknown_period_falls_back_to_seven_days(client, admin):
    r = client.get("/admin/score-verification?days=5", cookies=admin)
    assert r.status_code == 200
    assert 'class="on">Last 7 days' in r.text


def test_page_is_admin_only(client, monkeypatch):
    import admin_routes
    monkeypatch.setattr(admin_routes, "ADMIN_EMAILS", {"boss@example.com"})
    for cookies in ({}, {"session": _session_cookie("player@example.com")}):
        r = client.get("/admin/score-verification", cookies=cookies, follow_redirects=False)
        assert r.status_code == 403


def test_dashboard_links_to_the_page(client, admin):
    assert 'href="/admin/score-verification"' in client.get("/admin", cookies=admin).text
