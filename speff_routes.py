"""
speff_routes.py — 2026 Speff (Speed + Efficiency) Championship.

Four leaderboards: Beginner, Intermediate, Expert, and Combined.
Qualifying games: 100% click efficiency (bbbv == left_clicks + coalesce(chord_clicks, 0))
on standard board sizes, played in 2026 by logged-in users.

Route: GET /speff/2026?tab={beginner|intermediate|expert|combined}
"""
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup, escape
from sqlalchemy import func
from sqlalchemy.orm import Session
from starlette.config import Config

from database import GameHistory, UserProfile, get_db
from auth import get_current_user
from translations import get_lang, get_t, FUN_LANGS
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs
from game_catalog import PUZZLE_GAMES
from quest_catalog import quest_config
import settings as site_settings

speff_router = APIRouter()

# ── Jinja2 helpers ─────────────────────────────────────────────────────────────

def _autolink(text):
    if not text:
        return Markup('')
    safe = str(escape(text))
    def _replace(m):
        url = m.group(0)
        while url and url[-1] in '.,;:!?)]\'\"':
            url = url[:-1]
        return '<a href="{u}" target="_blank" rel="noopener noreferrer">{u}</a>'.format(u=url)
    return Markup(re.sub(r'https?://[^\s<>"\'\x00-\x1f]+', _replace, safe))  # nosec B704

def _ms_to_s(ms):
    """Format milliseconds as a seconds string with 3 decimal places."""
    if ms is None:
        return "—"
    return f"{ms / 1000:.3f}"

_cfg = Config(".env")

templates = Jinja2Templates(directory="templates")
templates.env.globals["get_breadcrumbs"]        = _get_breadcrumbs
templates.env.globals["quest_config"]           = quest_config
templates.env.globals["puzzle_games"]           = PUZZLE_GAMES
templates.env.globals["DEFAULT_SKIN"]           = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]            = site_settings.active_skin
templates.env.globals["solstice_banner"]        = site_settings.solstice_banner
templates.env.globals["equinox_banner"]         = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"]  = site_settings.diana_birthday_banner
templates.env.globals["mexico_banner"]          = site_settings.mexico_banner
templates.env.globals["is_mexico_cinco"]        = site_settings.is_mexico_cinco
templates.env.globals["is_mexico_independence"] = site_settings.is_mexico_independence
templates.env.globals["page_localized"]         = False
templates.env.globals["FUN_LANGS"]              = FUN_LANGS
templates.env.globals["ga_tag"]                 = _cfg("GA_TAG", default="")
templates.env.globals["twitter_handle"]         = _cfg("TWITTER_HANDLE", default="")
templates.env.filters["autolink"]               = _autolink
templates.env.filters["ms_to_s"]                = _ms_to_s

# ── Championship constants ─────────────────────────────────────────────────────

CHAMP_YEAR  = 2026
CHAMP_START = datetime(2026, 1, 1, tzinfo=timezone.utc)
CHAMP_END   = datetime(2027, 1, 1, tzinfo=timezone.utc)

_BOARDS = {
    "beginner":     {"rows": 9,  "cols": 9,  "mines": 10},
    "intermediate": {"rows": 16, "cols": 16, "mines": 40},
    "expert":       {"rows": 30, "cols": 16, "mines": 99},
}
_VALID_TABS = ("beginner", "intermediate", "expert", "combined")

# ── Query helpers ──────────────────────────────────────────────────────────────

def _qualifying_subquery(db: Session, mode: str):
    """Subquery → (user_email, best_ms): best 100%-efficiency time per user for one mode."""
    b = _BOARDS[mode]
    return (
        db.query(
            GameHistory.user_email,
            func.min(GameHistory.time_ms).label("best_ms"),
        )
        .filter(
            GameHistory.mode  == mode,
            GameHistory.rows  == b["rows"],
            GameHistory.cols  == b["cols"],
            GameHistory.mines == b["mines"],
            GameHistory.time_ms.isnot(None),
            GameHistory.bbbv.isnot(None),
            GameHistory.left_clicks.isnot(None),
            # 100% efficiency: bbbv equals total opening clicks (left + chord)
            GameHistory.bbbv == GameHistory.left_clicks + func.coalesce(GameHistory.chord_clicks, 0),
            GameHistory.created_at >= CHAMP_START,
            GameHistory.created_at <  CHAMP_END,
        )
        .group_by(GameHistory.user_email)
        .subquery()
    )


def _individual_board(db: Session, mode: str, limit: int = 200) -> list:
    sq = _qualifying_subquery(db, mode)
    rows = (
        db.query(
            sq.c.user_email,
            sq.c.best_ms,
            UserProfile.display_name,
            UserProfile.public_id,
        )
        .outerjoin(UserProfile, UserProfile.email == sq.c.user_email)
        .order_by(sq.c.best_ms.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank":      i + 1,
            "email":     r.user_email,
            "name":      r.display_name or r.user_email.split("@")[0],
            "public_id": r.public_id,
            "time_ms":   r.best_ms,
        }
        for i, r in enumerate(rows)
    ]


def _combined_board(db: Session, limit: int = 200) -> list:
    """Combined: inner-join all three modes; only players who have all three qualify."""
    sq_b = _qualifying_subquery(db, "beginner")
    sq_i = _qualifying_subquery(db, "intermediate")
    sq_e = _qualifying_subquery(db, "expert")
    total = (sq_b.c.best_ms + sq_i.c.best_ms + sq_e.c.best_ms).label("total_ms")
    rows = (
        db.query(
            sq_b.c.user_email,
            sq_b.c.best_ms.label("beg_ms"),
            sq_i.c.best_ms.label("int_ms"),
            sq_e.c.best_ms.label("exp_ms"),
            total,
            UserProfile.display_name,
            UserProfile.public_id,
        )
        .join(sq_i, sq_i.c.user_email == sq_b.c.user_email)
        .join(sq_e, sq_e.c.user_email == sq_b.c.user_email)
        .outerjoin(UserProfile, UserProfile.email == sq_b.c.user_email)
        .order_by(total.asc())
        .limit(limit)
        .all()
    )
    return [
        {
            "rank":      i + 1,
            "email":     r.user_email,
            "name":      r.display_name or r.user_email.split("@")[0],
            "public_id": r.public_id,
            "beg_ms":    r.beg_ms,
            "int_ms":    r.int_ms,
            "exp_ms":    r.exp_ms,
            "total_ms":  r.total_ms,
        }
        for i, r in enumerate(rows)
    ]

# ── Route ──────────────────────────────────────────────────────────────────────

@speff_router.get("/speff/2026", response_class=HTMLResponse)
def speff_2026(request: Request, tab: str = "combined", db: Session = Depends(get_db)):
    lang = get_lang(request)
    t    = get_t(request)
    user = get_current_user(request)
    if tab not in _VALID_TABS:
        tab = "combined"
    boards = {
        "beginner":     _individual_board(db, "beginner"),
        "intermediate": _individual_board(db, "intermediate"),
        "expert":       _individual_board(db, "expert"),
        "combined":     _combined_board(db),
    }
    return templates.TemplateResponse(request, "speff.html", {
        "lang":   lang,
        "t":      t,
        "user":   user,
        "tab":    tab,
        "boards": boards,
        "year":   CHAMP_YEAR,
    })
