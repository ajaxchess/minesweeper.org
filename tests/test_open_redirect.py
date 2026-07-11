"""
tests/test_open_redirect.py — _safe_relative_url() open-redirect guard.

Covers two real gaps found while investigating CodeQL alerts #184/#185
(those two exact alerts turned out to be stale — already fixed elsewhere —
but the audit that checked them turned up these):

  1. Backslash-based bypass ("/\\evil.com"). Per the WHATWG URL spec,
     browsers treat \\ as equivalent to / for special schemes (http, https,
     ws, wss, ftp, file), so a value that Python's urlparse sees as a
     harmless relative path (empty netloc) can still be resolved by a
     browser as a protocol-relative redirect to another origin.
  2. Two call sites — the OAuth `next` param flow and
     lang_prefix_middleware's `?lang=en` redirect — either had their own
     hand-rolled startswith("//") check with the same blind spot, or (for
     the middleware) no check at all. Both now route through
     _safe_relative_url() instead.
"""
import asyncio

import pytest
from starlette.requests import Request

from main import _safe_relative_url, lang_prefix_middleware

# ── Direct unit tests of the sanitizer ────────────────────────────────────────

BYPASS_ATTEMPTS = [
    "//evil.com",              # classic protocol-relative
    "///evil.com",             # extra slash, still protocol-relative
    "/\\evil.com",             # backslash bypass — the gap this fix closes
    "\\/evil.com",
    "\\\\evil.com",
    "/\\/evil.com",
    "http://evil.com",         # absolute URL, different scheme
    "https://evil.com",
    "http:evil.com",           # scheme without //
]


@pytest.mark.parametrize("bad_url", BYPASS_ATTEMPTS)
def test_safe_relative_url_rejects_bypass_attempts(bad_url):
    assert _safe_relative_url(bad_url) == "/"


@pytest.mark.parametrize("good_url", [
    "/",
    "/dashboard",
    "/pvp?x=1",
    "/2026worldcup/mexico",
    "/duel/abc123",
])
def test_safe_relative_url_allows_legitimate_paths(good_url):
    assert _safe_relative_url(good_url) == good_url


def test_safe_relative_url_custom_fallback():
    assert _safe_relative_url("//evil.com", fallback="/home") == "/home"


# ── Integration tests: real routes that rely on the sanitizer ────────────────

def test_legacy_login_redirect_sanitizes_protocol_relative_next(client):
    r = client.get("/login?next=//evil.com", follow_redirects=False)
    assert r.status_code == 302
    assert "evil.com" not in r.headers["location"]


def test_legacy_login_redirect_sanitizes_backslash_next(client):
    r = client.get("/login?next=/\\evil.com", follow_redirects=False)
    assert r.status_code == 302
    assert "evil.com" not in r.headers["location"]


def test_legacy_login_redirect_allows_safe_next(client):
    r = client.get("/login?next=/pvp", follow_redirects=False)
    assert r.status_code == 302
    # quote(next_url, safe='/') leaves "/" unescaped, so this is exact.
    assert r.headers["location"] == "/auth/login?next=/pvp"


# ── Direct test of the middleware branch (bypasses TestClient's own URL
# parsing, which may normalize a literal "//" path before it ever reaches the
# app — constructing the ASGI scope by hand reproduces exactly what a raw
# HTTP request line like "GET //evil.com?lang=en" would hand the app) ────────

def test_lang_prefix_middleware_blocks_protocol_relative_en_redirect():
    scope = {
        "type": "http",
        "method": "GET",
        "path": "//evil.com",
        "query_string": b"lang=en",
        "headers": [],
    }
    request = Request(scope)

    async def call_next(_req):
        raise AssertionError("call_next should not run — this request must redirect")

    response = asyncio.run(lang_prefix_middleware(request, call_next))
    assert response.status_code == 301
    assert "evil.com" not in response.headers["location"]
