def test_news_link_and_logo_render_on_homepage(client):
    r = client.get("/")
    assert r.status_code == 200
    assert 'href="/blog"' in r.text
    assert ">News<" in r.text
    assert "/static/img/minesweeper-org-logo.webp" in r.text
    assert "/static/img/minesweeper-org-logo.png" in r.text
    assert "Lady Di's Mines classic Minesweeper logo" in r.text
    assert "Minesweeper.org logo with minesweeper tiles" in r.text
    assert '<span class="logo-text">Minesweeper.org</span>' not in r.text


def test_blog_index_is_presented_as_news(client):
    r = client.get("/blog")
    assert r.status_code == 200
    assert "Minesweeper.org News" in r.text
    assert "Minesweeper News" in r.text


def test_blog_post_has_previous_next_navigation(client):
    r = client.get("/blog/traffic-growth")
    assert r.status_code == 200
    assert "All News" in r.text
    assert "Previous Post" in r.text
    assert "Next Post" in r.text
    assert 'rel="prev"' in r.text
    assert 'rel="next"' in r.text
