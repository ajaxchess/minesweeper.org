"""
blog_routes.py — Blog page and API route handlers for minesweeper.org.
Mount this router in main.py with: app.include_router(blog_router)
"""
import os
import re
from datetime import date as _date
import datetime

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

from database import BlogComment, get_db
from admin_routes import require_user
from auth import get_current_user
from translations import get_lang, get_t
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

blog_router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

templates = Jinja2Templates(directory="templates")
templates.env.globals["quest_config"]          = quest_config
templates.env.globals["DEFAULT_SKIN"]          = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]           = site_settings.active_skin
templates.env.globals["solstice_banner"]       = site_settings.solstice_banner
templates.env.globals["equinox_banner"]        = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"] = site_settings.diana_birthday_banner
templates.env.globals["mexico_banner"]         = site_settings.mexico_banner
templates.env.globals["is_mexico_cinco"]       = site_settings.is_mexico_cinco
templates.env.globals["is_mexico_independence"] = site_settings.is_mexico_independence
templates.env.globals["ga_tag"]               = ""  # not needed in blog routes
templates.env.globals["get_breadcrumbs"]      = _get_breadcrumbs


# ── Blog ──────────────────────────────────────────────────────────────────────

# Post registry — add a new entry here for each new post.
# date:    ISO 8601 date string (YYYY-MM-DD)
# file:    path relative to the repo root
# excerpt: one-sentence summary shown on the index page
BLOG_POSTS = [
    {
        "slug":          "down-with-interstitials",
        "file":          "blog/down-with-interstitials.md",
        "title":         "Down with Interstitials!",
        "date":          "2026-05-10",
        "datePublished": "2026-05-10T00:00:00Z",
        "image":         "/static/img/roadblocks.jpg",
        "excerpt":       "Interstitials are full-screen ads that ambush you the moment you finish "
                         "a game and want to start another. We don't have them — on the site or "
                         "the app. Finish a game and go again, immediately.",
    },
    {
        "slug":          "taking-the-show-on-the-road",
        "file":          "blog/taking-the-show-on-the-road.md",
        "title":         "Taking the Show on the Road",
        "date":          "2026-05-09",
        "datePublished": "2026-05-09T00:00:00Z",
        "image":         "/static/img/roadview.jpeg",
        "excerpt":       "The minesweeper.org iOS app is live — play on the go, keep your "
                         "leaderboard access, and start a new game the moment you finish the last one. "
                         "No unskippable ads. Android is coming soon.",
    },
    {
        "slug":          "nononoguess",
        "file":          "blog/nononoguess.md",
        "title":         "Nonosweeper's No Guess Mode: Every Puzzle, Solvable by Logic Alone",
        "date":          "2026-04-11",
        "datePublished": "2026-04-11T00:00:00Z",
        "image":         "/static/img/Nono_Guess_Required.png",
        "excerpt":       "Not every randomly-generated nonogram plays fair — sometimes the clues "
                         "leave a 50/50 guess at the end. No Guess mode runs a constraint-propagation "
                         "solver on every candidate board and only presents puzzles that are fully "
                         "solvable by logic alone.",
    },
    {
        "slug":          "traffic-growth",
        "file":          "blog/traffic-growth.md",
        "title":         "We're Growing — When Will We Hit 100,000 Daily Visitors?",
        "date":          "2026-04-11",
        "datePublished": "2026-04-11T00:00:00Z",
        "image":         "/static/img/minesweeper_org_Linear_Fit.png",
        "excerpt":       "We fitted a linear + weekly-periodic model to 17 days of traffic data "
                         "and asked: when does minesweeper.org reach 100,000 daily unique IPs? "
                         "The answer ranges from October 2026 to November 2040, depending on which "
                         "growth curve we're actually on.",
    },
    {
        "slug":          "rodential-heroics",
        "file":          "blog/magawa-hero-rat-wnm.md",
        "title":         "Rodential Heroics",
        "date":          "2026-04-10",
        "datePublished": "2026-04-10T15:00:00Z",
        "image":         "/static/img/Magawa_in_2020.jpg",
        "excerpt":       "There is a seven-foot stone statue in Siem Reap, Cambodia, depicting a rat "
                         "wearing a gold medal. When you learn what Magawa did to earn it, "
                         "it might be among the most deserved monuments in the world.",
    },
    {
        "slug":          "multicloud",
        "file":          "blog/multicloud.md",
        "title":         "Minesweeper.org Goes Multicloud",
        "date":          "2026-04-05",
        "datePublished": "2026-04-05T00:00:00Z",
        "image":         "/static/img/toby-learned-pig-c6c4ff-small.webp",
        "excerpt":       "The Lady Di's Mines team has spun up a GCP instance at pgl.minesweeper.org "
                         "in support of the native Pig Latin speakers of Iowa.",
    },
    {
        "slug":          "royalty-free",
        "file":          "blog/15puzzle-generator.md",
        "title":         "Nothing About Her Is Royalty-Free",
        "date":          "2026-04-03",
        "datePublished": "2026-04-03T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/Diana_Princess_of_Wales_1997.jpg",
        "excerpt": "Searching for a royalty-free photo of Diana, Princess of Wales, "
                   "to demo our new 15-Puzzle Generator. It turns out that's complicated.",
    },
    {
        "slug":          "fifteen-puzzle",
        "file":          "blog/15puzzle_article.md",
        "title":         "The new 15-puzzle!",
        "date":          "2026-03-31",
        "datePublished": "2026-03-31T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/Diana15Puzzle.png",
        "excerpt": "Minesweeper.org has a new sliding tile puzzle: the 15-Puzzle. "
                   "Play the daily challenge, upload your own photo, and slide whole rows in one move.",
    },
    {
        "slug":          "tentaizu-theme",
        "file":          "blog/tentaizu-theme.md",
        "title":         "The new Tentaizu Theme",
        "date":          "2026-03-20",
        "datePublished": "2026-03-20T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/TentaizuPuzzle20260320Equinox.png",
        "excerpt": "Lady Di's Mines now switches to the Tentaizu theme on solstices and equinoxes. "
                   "Here's what the theme is and a little about the Tentaizu puzzle.",
    },
    {
        "slug":          "no-jira-required",
        "file":          "blog/2_saaspocalypse-kanban.md",
        "title":         "No Jira Required: GitAgile Kanban in Your Repo",
        "date":          "2026-03-19",
        "datePublished": "2026-03-19T12:00:00Z",
        "excerpt": "Instead of subscribing to Jira, Claude Code built a kanban board "
                   "that reads directly from a markdown file in the repo. "
                   "The SaaSpocalypse comes for project management.",
    },
    {
        "slug":          "3bv",
        "file":          "blog/3bv_blog_post.md",
        "title":         "We've added 3BV values to Lady Di's Mines",
        "date":          "2026-03-18",
        "datePublished": "2026-03-18T00:00:00Z",
        "image":         "https://minesweeper.org/static/img/3BV_Example.png",
        "excerpt": "Lady Di's Mines now displays 3BV — Bechtel's Board Benchmark Value — "
                   "the minimum clicks needed to clear a board. Here's what it means and why it matters.",
    },
    {
        "slug":    "lady-di",
        "file":    "blog/lady-di-blog-post.md",
        "title":   "She's Back: The Return of Lady Di's Mines",
        "date":          "2026-03-15",
        "datePublished": "2026-03-15T15:00:00Z",
        "excerpt": "I built the original minesweeper.org in 1999 as a Physics PhD student. "
                   "Here's the story of Lady Di's Mines — and why she's back.",
    },
    {
        "slug":          "saaspocalypse",
        "file":          "blog/1_saaspocalypse-blog-post.md",
        "title":         "SaaSpocalypse.Now!",
        "date":          "2026-03-14",
        "datePublished": "2026-03-14T15:00:00Z",
        "excerpt": "AI coding tools have collapsed the distance between "
                   "'I want a thing' and 'I have the thing.' "
                   "Meet the SaaSpocalypse.",
    },
]


def _blog_post_meta(post: dict) -> dict:
    """Attach display-friendly date; return enriched copy."""
    try:
        d = datetime.date.fromisoformat(post["date"])
        display = d.strftime("%B %-d, %Y")
    except Exception:
        display = post["date"]
    return {**post, "date_display": display}


_BLOG_INDEX = [_blog_post_meta(p) for p in BLOG_POSTS]
_BLOG_BY_SLUG = {p["slug"]: p for p in _BLOG_INDEX}


@blog_router.get("/blog", response_class=HTMLResponse)
async def blog_index(request: Request):
    lang = get_lang(request)
    return templates.TemplateResponse(request, "blog_index.html", {
        "mode": "blog",
        "user": get_current_user(request),
        "lang": lang, "t": get_t(request),
        "posts": _BLOG_INDEX,
        "noindex": lang != "en",
    })


def _parse_front_matter(raw: str) -> tuple[dict, str]:
    """Extract YAML front matter from markdown. Returns (meta dict, body text)."""
    meta = {}
    # Strip UTF-8 BOM if present
    raw = raw.lstrip("﻿")
    # Normalise line endings
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    m = re.match(r"^---\n(.*?\n)---\n", raw, re.DOTALL)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                key, _, val = line.partition(":")
                meta[key.strip()] = val.strip().strip('"').strip("'")
        raw = raw[m.end():].lstrip("\n")
    return meta, raw


def _make_absolute_url(request: Request, url: str) -> str:
    """Return an absolute URL, resolving relative paths against the request base URL."""
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    base = str(request.base_url).rstrip("/")
    return base + ("" if url.startswith("/") else "/") + url


def _webp_if_exists(image_url: str) -> str:
    """Return the .webp URL only if the file exists on disk, else empty string."""
    if not image_url.endswith(".png"):
        return ""
    webp_url = image_url.replace(".png", ".webp")
    local_path = webp_url.replace("https://minesweeper.org/", "")
    return webp_url if os.path.exists(local_path) else ""


@blog_router.get("/blog/{slug}", response_class=HTMLResponse)
async def blog_post(request: Request, slug: str, db: Session = Depends(get_db)):
    import markdown as md_lib
    post = _BLOG_BY_SLUG.get(slug)
    if not post:
        return Response(status_code=404)
    _path = os.path.join(os.path.dirname(os.path.abspath(__file__)), post["file"])
    try:
        with open(_path, encoding="utf-8") as _f:
            raw = _f.read()
    except OSError:
        return Response(status_code=404)
    front_matter, body = _parse_front_matter(raw)
    lines = body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    html_content = md_lib.markdown("\n".join(lines), extensions=["extra", "sane_lists"])
    date_published = (
        front_matter.get("datePublished")
        or post.get("datePublished")
        or post["date"]
    )
    date_modified = (
        front_matter.get("dateModified")
        or post.get("dateModified")
        or date_published
    )
    comments = (
        db.query(BlogComment)
        .filter_by(post_slug=slug, approved=True)
        .order_by(BlogComment.created_at)
        .all()
    )
    post_index = next((i for i, p in enumerate(_BLOG_INDEX) if p["slug"] == slug), -1)
    newer_post = _BLOG_INDEX[post_index - 1] if post_index > 0 else None
    older_post = _BLOG_INDEX[post_index + 1] if 0 <= post_index < len(_BLOG_INDEX) - 1 else None
    return templates.TemplateResponse(request, "blog_post.html", {
        "mode": "blog",
        "user":           get_current_user(request),
        "lang":           get_lang(request), "t": get_t(request),
        "post":           post,
        "newer_post":     newer_post,
        "older_post":     older_post,
        "content":        html_content,
        "author":         front_matter.get("author", "") or "minesweeper.org",
        "authorurl":      front_matter.get("authorurl", "") if front_matter.get("authorurl", "").startswith(("https://", "http://")) else "",
        "publisher":      front_matter.get("publisher", "") or "minesweeper.org",
        "og_image":       _make_absolute_url(request, post.get("image") or front_matter.get("image", "")),
        "og_image_webp":  _webp_if_exists(post.get("image") or front_matter.get("image", "")),
        "date_published": date_published,
        "date_modified":  date_modified,
        "comments":       comments,
        "page_title":     post["title"] + " — minesweeper.org News" if len(post["title"]) + len(" — minesweeper.org News") <= 60 else post["title"],
        "noindex":        get_lang(request) != "en",
    })


@blog_router.post("/api/blog/{slug}/comments")
@limiter.limit("10/minute")
async def submit_blog_comment(slug: str, request: Request, db: Session = Depends(get_db)):
    user = require_user(request)
    if slug not in _BLOG_BY_SLUG:
        raise HTTPException(status_code=404, detail="Post not found")
    data = await request.json()
    body = (data.get("body") or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Comment body required")
    if len(body) > 2000:
        raise HTTPException(status_code=400, detail="Comment too long (max 2000 chars)")
    comment = BlogComment(
        post_slug=slug,
        user_email=user["email"],
        display_name=user.get("display_name") or user.get("name") or user["email"],
        body=body,
        approved=False,
    )
    db.add(comment)
    db.commit()
    return {"ok": True, "message": "Your comment has been submitted and is awaiting review."}
