"""
tests/test_health.py — Smoke tests for utility/static endpoints.
"""


def test_health_localhost_only(client):
    """/health is restricted to 127.0.0.1; TestClient appears as 'testclient', not localhost."""
    r = client.get("/health")
    # The endpoint enforces localhost-only access — non-local requests get 403.
    # On the real server, curl localhost/health returns 200.
    assert r.status_code == 403


def test_robots_txt(client):
    r = client.get("/robots.txt")
    assert r.status_code == 200
    assert "User-agent" in r.text


def test_ads_txt(client):
    r = client.get("/ads.txt")
    assert r.status_code == 200


def test_sitemap_xml(client):
    r = client.get("/sitemap.xml")
    assert r.status_code == 200
    assert "urlset" in r.text or "sitemap" in r.text.lower()


def test_homepage_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "minesweeper" in r.text.lower()


def test_404_returns_html(client):
    r = client.get("/this-page-definitely-does-not-exist-xyz")
    assert r.status_code == 404
    # Custom 404 template should render, not a bare JSON response
    assert "html" in r.headers.get("content-type", "").lower()
