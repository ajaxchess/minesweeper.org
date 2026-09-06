"""
tests/test_csrf.py — CSRF middleware (X-Requested-With: XMLHttpRequest guard).

The middleware allows requests that carry X-Requested-With: XMLHttpRequest OR
Content-Type: application/json (both are unforgeable cross-origin without a
CORS preflight). Tests that expect a 403 must therefore send neither header —
using content= (raw bytes, no Content-Type) rather than json= (which
automatically sets Content-Type: application/json and would pass CSRF).
"""
import json as _json
from conftest import XHR

# A minimal valid score payload (used only to reach the CSRF check layer)
_SCORE = {
    "name": "Alice",
    "mode": "beginner",
    "time_secs": 30,
    "rows": 9,
    "cols": 9,
    "mines": 10,
}


def test_post_without_xhr_header_is_rejected(client):
    """POST /api/scores with no XHR header and no application/json Content-Type must return 403."""
    r = client.post("/api/scores", content=_json.dumps(_SCORE).encode())
    assert r.status_code == 403
    assert "CSRF" in r.json().get("detail", "")


def test_post_with_xhr_header_passes_csrf(client):
    """POST /api/scores with correct header must not return 403."""
    r = client.post("/api/scores", json=_SCORE, headers=XHR)
    # 201 = accepted; 422 = validation error — either means CSRF passed
    assert r.status_code in (201, 422)


def test_get_requests_never_blocked(client):
    """GET /api/* must never be blocked by the CSRF check."""
    r = client.get("/api/scores/beginner")
    assert r.status_code != 403


def test_csrf_rejects_all_api_post_routes(client):
    """Spot-check several POST /api/* routes all reject without the header."""
    endpoints = [
        ("/api/mosaic-scores",        {"name": "X", "puzzle_date": "2026-01-01", "time_secs": 60}),
        ("/api/tentaizu-scores",      {"name": "X", "puzzle_date": "2026-01-01", "time_secs": 60}),
        ("/api/cylinder-scores",      {"name": "X", "cyl_mode": "easy", "time_secs": 10,
                                       "rows": 9, "cols": 9, "mines": 10}),
        ("/api/mosaic-custom-scores", {"board_hash": "abc", "board_mask": "", "rows": 9,
                                       "cols": 9, "name": "X", "time_secs": 30}),
    ]
    for path, payload in endpoints:
        r = client.post(path, content=_json.dumps(payload).encode())
        assert r.status_code == 403, f"{path} did not return 403 without XHR header"
