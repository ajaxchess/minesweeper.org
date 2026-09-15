"""
wc2026_routes.py — Page and API route handlers for the 2026 FIFA World Cup Celebration (F97).
Mount this router in main.py with: app.include_router(wc2026_router)
"""
import json as _json
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import func
from sqlalchemy.orm import Session

from wc2026_data import (
    WC2026_COUNTRIES, WC2026_BY_SLUG, WC2026_BY_GROUP,
    WC2026_GROUPS, VALID_WC2026_SLUGS, WC2026_EASY, WC2026_HARD,
    WC2026_ROUND_ORDER, WC2026_ROUND_LABELS,
)
from wc2026_board import get_or_create_board, board_to_dict, _make_board
from database import (
    UserProfile, WC2026Match, WC2026BoardState, WC2026Score,
    get_db,
)
from auth import get_current_user
from translations import get_lang, get_t, TRANSLATIONS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

wc2026_router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

templates = Jinja2Templates(directory="templates")
templates.env.globals["quest_config"]           = quest_config
templates.env.globals["DEFAULT_SKIN"]           = site_settings.DEFAULT_SKIN
templates.env.globals["active_skin"]            = site_settings.active_skin
templates.env.globals["solstice_banner"]        = site_settings.solstice_banner
templates.env.globals["equinox_banner"]         = site_settings.equinox_banner
templates.env.globals["diana_birthday_banner"]  = site_settings.diana_birthday_banner
templates.env.globals["mexico_banner"]          = site_settings.mexico_banner
templates.env.globals["is_mexico_cinco"]        = site_settings.is_mexico_cinco
templates.env.globals["is_mexico_independence"] = site_settings.is_mexico_independence
templates.env.globals["ga_tag"]                 = ""
templates.env.globals["get_breadcrumbs"]        = _get_breadcrumbs


# ── Module-level adjacency cache for WC2026 flood-reveal ─────────────────────
# Keyed by (board_row_id, rr, cc) so adj counts persist across reveal requests
# for the same board without mixing data from different mine layouts.
_adj_cache: dict = {}


# ── 2026 FIFA World Cup teams ─────────────────────────────────────────────────
WC2026_TEAMS: list[tuple[str, str]] = [
    ("dz",     "Algeria"),
    ("ar",     "Argentina"),
    ("au",     "Australia"),
    ("at",     "Austria"),
    ("be",     "Belgium"),
    ("ba",     "Bosnia & Herzegovina"),
    ("br",     "Brazil"),
    ("ca",     "Canada"),
    ("cv",     "Cape Verde"),
    ("co",     "Colombia"),
    ("hr",     "Croatia"),
    ("cz",     "Czechia"),
    ("cd",     "DR Congo"),
    ("ec",     "Ecuador"),
    ("eg",     "Egypt"),
    ("gb-eng", "England"),
    ("fr",     "France"),
    ("de",     "Germany"),
    ("gh",     "Ghana"),
    ("ht",     "Haiti"),
    ("ir",     "Iran"),
    ("iq",     "Iraq"),
    ("ci",     "Ivory Coast"),
    ("jp",     "Japan"),
    ("jo",     "Jordan"),
    ("mx",     "Mexico"),
    ("ma",     "Morocco"),
    ("nl",     "Netherlands"),
    ("nz",     "New Zealand"),
    ("no",     "Norway"),
    ("pa",     "Panama"),
    ("py",     "Paraguay"),
    ("pt",     "Portugal"),
    ("sa",     "Saudi Arabia"),
    ("gb-sct", "Scotland"),
    ("sn",     "Senegal"),
    ("za",     "South Africa"),
    ("kr",     "South Korea"),
    ("es",     "Spain"),
    ("se",     "Sweden"),
    ("ch",     "Switzerland"),
    ("tn",     "Tunisia"),
    ("tr",     "Türkiye"),
    ("uy",     "Uruguay"),
    ("us",     "USA"),
    ("uz",     "Uzbekistan"),
]
VALID_WC2026_CODES: frozenset[str] = frozenset(code for code, _ in WC2026_TEAMS)


# ── Constants ─────────────────────────────────────────────────────────────────
# Light anti-abuse: cap guest-earned WC points per cookie per UTC day.
# Combined with the per-IP slowapi rate limit on /solve, this is the project's
# "light defense" level — sufficient given that admin score-review channels
# exist for genuine concerns.
WC2026_GUEST_DAILY_POINT_CAP = 200


# ── Pydantic models ───────────────────────────────────────────────────────────

class WC2026FanUpdate(BaseModel):
    team: Optional[str] = None

class WC2026RevealPayload(BaseModel):
    idx: int

class WC2026FlagPayload(BaseModel):
    idx: int

class WC2026SolvePayload(BaseModel):
    time_ms:      Optional[int] = None
    bbbv:         Optional[int] = None
    left_clicks:  Optional[int] = None
    right_clicks: Optional[int] = None

class WC2026FanSet(BaseModel):
    team: str


# ── Helper functions ──────────────────────────────────────────────────────────

def _wc_player_identity(request: Request, db: Session) -> dict:
    """Identify the WC player as either a logged-in user or an anonymous guest.

    Returns a dict with: email (str|None), guest_token (str|None), fan_flag (str|None).
    Exactly one of email / guest_token is non-None. The guest_token is issued
    lazily so unauthenticated GETs of public WC pages don't churn cookies for
    visitors who never play.

    To force-issue a guest token (e.g. before a write), call `_wc_ensure_guest_token`.
    """
    user = get_current_user(request)
    if user:
        profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
        return {
            "email":       user["email"],
            "guest_token": None,
            "fan_flag":    (profile.wc2026_fan if profile else None),
            "display_name": (profile.display_name if profile else user.get("display_name", "")),
        }
    token = request.session.get("guest_token")  # may be None
    return {
        "email":        None,
        "guest_token":  token,
        "fan_flag":     request.session.get("wc2026_fan"),
        "display_name": "Guest",
    }


def _wc_ensure_guest_token(request: Request) -> str:
    """Ensure the request.session carries a guest_token UUID; return it.

    Matches the existing project convention (see /api/scores guest fallback).
    """
    if "guest_token" not in request.session:
        request.session["guest_token"] = str(uuid.uuid4())
    return request.session["guest_token"]


def _wc_lookup_board(db: Session, identity: dict, slug: str, difficulty: str):
    """Look up an existing board row keyed by the player's identity.

    `identity` is the dict returned by `_wc_player_identity`. Returns None if
    no row exists (the caller decides whether to create one).
    """
    q = db.query(WC2026BoardState).filter_by(
        country_slug=slug, difficulty=difficulty
    )
    if identity["email"]:
        return q.filter_by(email=identity["email"]).first()
    if identity["guest_token"]:
        return q.filter_by(guest_token=identity["guest_token"]).first()
    return None  # guest with no token yet → no board possible


def _wc_guest_points_today(db: Session, guest_token: str) -> int:
    """Sum WC points earned by this guest_token since UTC midnight."""
    if not guest_token:
        return 0
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    total = (
        db.query(func.coalesce(func.sum(WC2026Score.total_points), 0))
        .filter(WC2026Score.guest_token == guest_token)
        .filter(WC2026Score.email.is_(None))
        .filter(WC2026Score.solved_at >= midnight)
        .scalar()
    )
    return int(total or 0)


def _wc_guest_team_pts(db: Session, guest_token: str | None, fan_flag: str | None) -> int:
    """Total points this guest_token has ever earned for their fan_flag country."""
    if not guest_token or not fan_flag:
        return 0
    total = (
        db.query(func.coalesce(func.sum(WC2026Score.total_points), 0))
        .filter(WC2026Score.guest_token == guest_token)
        .filter(WC2026Score.fan_flag == fan_flag)
        .filter(WC2026Score.email.is_(None))
        .scalar()
    )
    return int(total or 0)


def _wc_fan_banner(user, db: Session, request: Request | None = None) -> dict:
    """Return fan-flag context for WC pages.

    For logged-in users, the flag comes from UserProfile.wc2026_fan as before.
    For guests, the flag is read from the session cookie (set by /api/wc2026/set-fan).
    """
    if user:
        profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
        fan = profile.wc2026_fan if profile else None
    elif request is not None:
        fan = request.session.get("wc2026_fan")
    else:
        fan = None
    country = WC2026_BY_SLUG.get(fan) if fan else None
    return {"wc_fan": fan, "wc_fan_country": country}


_WC_CDT = ZoneInfo("America/Chicago")  # all published match times are CDT

def _localize_match(match_date: str, time_cdt: str, user_tz_str: Optional[str]) -> dict:
    """Return localized date/time/label for a WC match given an IANA tz string."""
    if not user_tz_str:
        return {"date_local": match_date, "time_local": time_cdt, "tz_label": "CDT"}
    try:
        user_tz = ZoneInfo(user_tz_str)
        h, m = map(int, time_cdt.split(":"))
        y, mo, d = map(int, match_date.split("-"))
        dt = datetime(y, mo, d, h, m, tzinfo=_WC_CDT).astimezone(user_tz)
        return {
            "date_local": dt.strftime("%Y-%m-%d"),
            "time_local": dt.strftime("%H:%M"),
            "tz_label":   dt.strftime("%Z"),
        }
    except Exception:
        return {"date_local": match_date, "time_local": time_cdt, "tz_label": "CDT"}


def _wc_match_dict(r: "WC2026Match", user_tz_str: Optional[str] = None) -> dict:
    """Shared row → dict mapping for WC2026Match, used by every match list below.

    team1/team2 fall back to {} (unknown slug) or an empty dict (no slug yet —
    knockout slot not resolved); templates use team1_label/team2_label
    ("Winner QF1", etc.) to render a placeholder until then.
    """
    return {
        "id": r.id, "group": r.group_name,
        "round": r.round, "round_label": WC2026_ROUND_LABELS.get(r.round, r.round),
        "date": r.match_date, "time_cdt": r.time_cdt, "city": r.city,
        "team1": WC2026_BY_SLUG.get(r.team1_slug, {}),
        "team2": WC2026_BY_SLUG.get(r.team2_slug, {}),
        "team1_slug": r.team1_slug, "team2_slug": r.team2_slug,
        "team1_label": r.team1_label, "team2_label": r.team2_label,
        "score1": r.score1, "score2": r.score2, "status": r.status,
        **_localize_match(r.match_date, r.time_cdt, user_tz_str),
    }


def _wc_matches_for_country(slug: str, db: Session,
                             user_tz_str: Optional[str] = None) -> list:
    rows = (
        db.query(WC2026Match)
        .filter(
            (WC2026Match.team1_slug == slug) | (WC2026Match.team2_slug == slug)
        )
        .order_by(WC2026Match.match_date, WC2026Match.time_cdt)
        .all()
    )
    return [_wc_match_dict(r, user_tz_str) for r in rows]


def _wc_group_matches(group: str, db: Session,
                      user_tz_str: Optional[str] = None) -> list:
    rows = (
        db.query(WC2026Match)
        .filter(WC2026Match.group_name == group)
        .order_by(WC2026Match.match_date, WC2026Match.time_cdt)
        .all()
    )
    return [_wc_match_dict(r, user_tz_str) for r in rows]


def _wc_knockout_matches(db: Session, user_tz_str: Optional[str] = None) -> dict:
    """All knockout-stage matches grouped by round, in bracket order.

    Returns {"rounds": [{"key","label","matches":[...]}, ...], "next_round": {...}|None}
    where next_round is the earliest round (bracket order) that isn't fully final yet —
    used to headline "next round of scheduled games" on the main page.
    """
    rows = (
        db.query(WC2026Match)
        .filter(WC2026Match.round != "group")
        .order_by(WC2026Match.match_date, WC2026Match.time_cdt)
        .all()
    )
    by_round: dict = {}
    for r in rows:
        by_round.setdefault(r.round, []).append(_wc_match_dict(r, user_tz_str))

    rounds = [
        {"key": rk, "label": WC2026_ROUND_LABELS.get(rk, rk), "matches": by_round[rk]}
        for rk in WC2026_ROUND_ORDER if rk in by_round
    ]
    next_round = next(
        (rd for rd in rounds if any(m["status"] != "final" for m in rd["matches"])),
        None,
    )
    return {"rounds": rounds, "next_round": next_round}


def _country_leaderboard(slug: str, db: Session, limit: int = 20) -> list:
    """Top fans (logged-in) of this country, by total points.

    Guest-keyed rows are excluded from this individual ranking — they roll into
    the country's total (via _fan_country_leaderboard) but not into a per-person
    row here. Logging in is what gets a player onto this board.
    """
    rows = (
        db.query(
            WC2026Score.email,
            WC2026Score.display_name,
            WC2026Score.fan_flag,
            func.sum(WC2026Score.total_points).label("pts"),
            func.min(WC2026Score.solve_time_ms).label("best_ms"),
        )
        .filter(WC2026Score.country_slug == slug)
        .filter(WC2026Score.email.isnot(None))
        .group_by(WC2026Score.email, WC2026Score.display_name, WC2026Score.fan_flag)
        .order_by(func.sum(WC2026Score.total_points).desc())
        .limit(limit)
        .all()
    )
    def fmt_time(ms):
        if ms is None: return None
        s = ms / 1000
        m = int(s // 60)
        return f"{m}:{s % 60:06.3f}" if m else f"{s % 60:.3f}s"
    result = []
    for r in rows:
        ci = WC2026_BY_SLUG.get(r.fan_flag, {})
        result.append({
            "display_name":  r.display_name,
            "fan_flag":      r.fan_flag,
            "fan_flag_img":  ci.get("flag", r.fan_flag),
            "fan_flag_name": ci.get("name", r.fan_flag),
            "points":        r.pts,
            "best_time":     fmt_time(r.best_ms),
        })
    return result


def _fan_country_leaderboard(db: Session, limit: int = 20) -> list:
    """Total fan points per country. Includes both logged-in and guest contributions —
    the country leaderboard is the union, since guests can earn for their team."""
    rows = (
        db.query(
            WC2026Score.fan_flag,
            func.sum(WC2026Score.total_points).label("pts"),
        )
        .group_by(WC2026Score.fan_flag)
        .order_by(func.sum(WC2026Score.total_points).desc())
        .limit(limit)
        .all()
    )
    result = []
    for r in rows:
        country = WC2026_BY_SLUG.get(r.fan_flag, {})
        result.append({"slug": r.fan_flag, "name": country.get("name", r.fan_flag),
                        "flag": country.get("flag", r.fan_flag), "points": r.pts})
    return result


def _individual_leaderboard(db: Session, limit: int = 20) -> list:
    """Top players overall (logged-in only — login is the carrot for the
    individual board). Guests can still earn points for their country via
    _fan_country_leaderboard, but they don't show up on this list."""
    rows = (
        db.query(
            WC2026Score.email,
            WC2026Score.display_name,
            WC2026Score.fan_flag,
            func.sum(WC2026Score.total_points).label("pts"),
        )
        .filter(WC2026Score.email.isnot(None))
        .group_by(WC2026Score.email, WC2026Score.display_name, WC2026Score.fan_flag)
        .order_by(func.sum(WC2026Score.total_points).desc())
        .limit(limit)
        .all()
    )
    return [{"display_name": r.display_name, "fan_flag": r.fan_flag,
             "fan_country": WC2026_BY_SLUG.get(r.fan_flag, {}), "points": r.pts}
            for r in rows]


# ── Page routes ───────────────────────────────────────────────────────────────

@wc2026_router.get("/team", response_class=HTMLResponse)
async def team_page(request: Request):
    return templates.TemplateResponse(request, "team.html", {
        "mode": "team",
        "user": get_current_user(request),
        "lang": get_lang(request), "t": get_t(request),
        "noindex": get_lang(request) != "en",
    })


@wc2026_router.get("/2026worldcup", response_class=HTMLResponse)
def wc2026_main(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    t    = get_t(request)
    lang = get_lang(request)
    fan_ctx   = _wc_fan_banner(user, db, request)
    groups    = {g: WC2026_BY_GROUP[g] for g in WC2026_GROUPS}
    country_lb = _fan_country_leaderboard(db)
    individual_lb = _individual_leaderboard(db)
    guest_token = None if user else request.session.get("guest_token")
    guest_team_pts = _wc_guest_team_pts(db, guest_token, fan_ctx.get("wc_fan"))
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first() if user else None
    user_tz = getattr(profile, "timezone", None) if profile else None
    knockout = _wc_knockout_matches(db, user_tz)
    # Noindex when this language has no translated wc2026 title (falls back to English).
    # Automatically lifts once meta_title_wc2026 is added to the language's TRANSLATIONS entry.
    _noindex = lang != "en" and "meta_title_wc2026" not in TRANSLATIONS.get(lang, {})
    return templates.TemplateResponse(request, "wc2026_main.html", {
        "user": user, "t": t,
        "lang": lang,
        "mode": "wc2026",
        "groups": groups,
        "group_list": WC2026_GROUPS,
        "country_lb": country_lb,
        "individual_lb": individual_lb,
        "wc2026_teams": WC2026_COUNTRIES,
        "guest_team_pts": guest_team_pts,
        "knockout_rounds": knockout["rounds"],
        "next_round": knockout["next_round"],
        "noindex": _noindex,
        **fan_ctx,
    })


@wc2026_router.get("/2026worldcup/{slug}", response_class=HTMLResponse)
def wc2026_country(slug: str, request: Request, db: Session = Depends(get_db)):
    if slug not in VALID_WC2026_SLUGS:
        raise HTTPException(status_code=404, detail="Country not found")
    user    = get_current_user(request)
    t       = get_t(request)
    lang    = get_lang(request)
    country = WC2026_BY_SLUG[slug]
    # Auto-select this country as the fan flag for guests who haven't chosen one yet
    if not user and not request.session.get("wc2026_fan"):
        request.session["wc2026_fan"] = slug
    fan_ctx = _wc_fan_banner(user, db, request)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first() if user else None
    user_tz = getattr(profile, "timezone", None) if profile else None
    matches = _wc_matches_for_country(slug, db, user_tz)
    group_countries = WC2026_BY_GROUP.get(country["group"], [])
    country_lb = _country_leaderboard(slug, db)

    # Render boards for anyone with a fan flag — logged-in users get email-keyed
    # boards, guests get guest_token-keyed boards. Visiting the page is enough
    # to issue a guest token; no write happens until the player flags/reveals.
    board_easy = board_hard = None
    if fan_ctx["wc_fan"]:
        if user:
            board_easy = board_to_dict(get_or_create_board(db, user["email"], slug, "easy"))
            board_hard = board_to_dict(get_or_create_board(db, user["email"], slug, "hard"))
        else:
            token = _wc_ensure_guest_token(request)
            board_easy = board_to_dict(get_or_create_board(
                db, None, slug, "easy", guest_token=token
            ))
            board_hard = board_to_dict(get_or_create_board(
                db, None, slug, "hard", guest_token=token
            ))

    # Noindex when this language's wc_country_title_suffix is unchanged from English
    # (title would be identical to the English page). Lifts automatically once a
    # real translated suffix is added to the language's TRANSLATIONS entry.
    _en_suffix = TRANSLATIONS["en"]["wc_country_title_suffix"]
    _noindex = lang != "en" and TRANSLATIONS.get(lang, {}).get("wc_country_title_suffix", _en_suffix) == _en_suffix
    return templates.TemplateResponse(request, "wc2026_country.html", {
        "user": user, "t": t,
        "lang": lang,
        "mode": "wc2026",
        "country": country,
        "matches": matches,
        "group_countries": group_countries,
        "country_lb": country_lb,
        "board_easy": board_easy,
        "board_hard": board_hard,
        "wc2026_teams": WC2026_COUNTRIES,
        "user_tz": user_tz,
        "noindex": _noindex,
        **fan_ctx,
    })


# ── API: profile fan setter ───────────────────────────────────────────────────

@wc2026_router.post("/api/profile/wc2026-fan")
def update_wc2026_fan(payload: WC2026FanUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Not logged in"}, status_code=401)
    profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
    if not profile:
        return JSONResponse({"error": "Profile not found"}, status_code=404)
    code = (payload.team or "").strip().lower() or None
    if code and code not in VALID_WC2026_CODES:
        return JSONResponse({"error": "Invalid team code"}, status_code=400)
    profile.wc2026_fan = code
    db.commit()
    return {"ok": True}


# ── API: board state ──────────────────────────────────────────────────────────

@wc2026_router.get("/api/wc2026/board/{slug}/{difficulty}")
def wc2026_get_board(slug: str, difficulty: str,
                     request: Request, db: Session = Depends(get_db)):
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")
    identity = _wc_player_identity(request, db)
    if identity["email"]:
        row = get_or_create_board(db, identity["email"], slug, difficulty)
    else:
        token = _wc_ensure_guest_token(request)
        row = get_or_create_board(db, None, slug, difficulty, guest_token=token)
    return board_to_dict(row)


@wc2026_router.post("/api/wc2026/board/{slug}/{difficulty}/reveal")
def wc2026_reveal(slug: str, difficulty: str, payload: WC2026RevealPayload,
                  request: Request, db: Session = Depends(get_db)):
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")
    identity = _wc_player_identity(request, db)
    row = _wc_lookup_board(db, identity, slug, difficulty)
    if not row or row.is_solved:
        return JSONResponse({"error": "No active board"}, status_code=400)

    spec   = WC2026_EASY if difficulty == "easy" else WC2026_HARD
    cells  = _json.loads(row.cell_state)
    mines  = {tuple(m) for m in _json.loads(row.mine_layout)}
    rows, cols = spec["rows"], spec["cols"]
    idx    = payload.idx

    if idx < 0 or idx >= rows * cols:
        return JSONResponse({"error": "Out of range"}, status_code=400)
    if cells[idx] != "hidden":
        return board_to_dict(row)

    r, c = divmod(idx, cols)
    if (r, c) in mines:
        cells[idx] = "exploded"
        row.cell_state = _json.dumps(cells)
        db.commit()
        return {**board_to_dict(row), "hit_mine": True}

    # BFS flood-reveal
    queue = deque([(r, c)])
    board_id = row.id
    def adj_count(rr, cc):
        key = (board_id, rr, cc)
        if key not in _adj_cache:
            _adj_cache[key] = sum(
                1 for dr in (-1,0,1) for dc in (-1,0,1)
                if (dr or dc) and 0 <= rr+dr < rows and 0 <= cc+dc < cols
                and (rr+dr, cc+dc) in mines
            )
        return _adj_cache[key]

    visited = set()
    while queue:
        rr, cc = queue.popleft()
        ii = rr * cols + cc
        if (rr, cc) in visited or cells[ii] != "hidden":
            continue
        visited.add((rr, cc))
        cells[ii] = "revealed"
        if adj_count(rr, cc) == 0:
            for dr in (-1,0,1):
                for dc in (-1,0,1):
                    nr, nc = rr+dr, cc+dc
                    if (dr or dc) and 0 <= nr < rows and 0 <= nc < cols:
                        if cells[nr*cols+nc] == "hidden":
                            queue.append((nr, nc))

    row.cell_state = _json.dumps(cells)
    db.commit()
    return {**board_to_dict(row), "hit_mine": False}


@wc2026_router.post("/api/wc2026/board/{slug}/{difficulty}/flag")
def wc2026_flag(slug: str, difficulty: str, payload: WC2026FlagPayload,
                request: Request, db: Session = Depends(get_db)):
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")
    identity = _wc_player_identity(request, db)
    row = _wc_lookup_board(db, identity, slug, difficulty)
    if not row or row.is_solved:
        return JSONResponse({"error": "No active board"}, status_code=400)

    spec  = WC2026_EASY if difficulty == "easy" else WC2026_HARD
    cells = _json.loads(row.cell_state)
    idx   = payload.idx
    if idx < 0 or idx >= spec["rows"] * spec["cols"]:
        return JSONResponse({"error": "Out of range"}, status_code=400)

    if cells[idx] == "hidden":
        cells[idx] = "flagged"
    elif cells[idx] == "flagged":
        cells[idx] = "hidden"

    row.cell_state = _json.dumps(cells)
    db.commit()
    return board_to_dict(row)


@wc2026_router.post("/api/wc2026/board/{slug}/{difficulty}/solve")
@limiter.limit("5/minute")
def wc2026_solve(slug: str, difficulty: str, payload: WC2026SolvePayload,
                 request: Request, db: Session = Depends(get_db)):
    """Called by the client when it detects all non-mine cells revealed.

    Accepts solves from logged-in users (points credited to their email) or
    guests with a session guest_token (points credited to the country only;
    guest rows are excluded from the individual "biggest fans" leaderboard).
    Mines that were not manually flagged are auto-flagged before saving.
    """
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")

    identity = _wc_player_identity(request, db)
    fan_flag = identity["fan_flag"]
    if not fan_flag:
        return JSONResponse({"error": "No fan flag set"}, status_code=400)

    row = _wc_lookup_board(db, identity, slug, difficulty)
    if not row or row.is_solved:
        return JSONResponse({"error": "Already solved or not found"}, status_code=400)

    spec   = WC2026_EASY if difficulty == "easy" else WC2026_HARD
    cells  = _json.loads(row.cell_state)
    mines  = {tuple(m) for m in _json.loads(row.mine_layout)}
    cols   = spec["cols"]

    # Verify: all non-mine cells must be revealed
    all_safe = all(
        s == "revealed"
        for i, s in enumerate(cells)
        if divmod(i, cols) not in mines
    )
    if not all_safe:
        return JSONResponse({"error": "Board not correctly solved"}, status_code=400)

    # Award points only for mines the player actually flagged; auto-flag the rest
    flags_correct = sum(
        1 for i, s in enumerate(cells)
        if divmod(i, cols) in mines and s == "flagged"
    )
    cells = [
        "flagged" if divmod(i, cols) in mines else s
        for i, s in enumerate(cells)
    ]
    row.cell_state = _json.dumps(cells)

    solve_bonus  = spec["solve_bonus"]
    total_points = flags_correct + solve_bonus

    # Light defense: cap a guest cookie's daily points. The solve still completes
    # (so the player sees their win), but excess points clamp to 0.
    capped = False
    if not identity["email"]:
        already = _wc_guest_points_today(db, identity["guest_token"] or "")
        remaining = max(0, WC2026_GUEST_DAILY_POINT_CAP - already)
        if total_points > remaining:
            total_points = remaining
            capped = True

    row.is_solved = True
    row.solved_at = datetime.now(timezone.utc)
    db.add(WC2026Score(
        email=identity["email"],
        guest_token=identity["guest_token"],
        display_name=identity["display_name"] or "Guest",
        country_slug=slug,
        difficulty=difficulty,
        fan_flag=fan_flag,
        flags_correct=flags_correct,
        solve_bonus=solve_bonus,
        solve_time_ms=payload.time_ms,
        bbbv=payload.bbbv,
        left_clicks=payload.left_clicks,
        right_clicks=payload.right_clicks,
        total_points=total_points,
    ))
    db.commit()
    return {
        "ok":            True,
        "flags_correct": flags_correct,
        "solve_bonus":   solve_bonus,
        "total_points":  total_points,
        "is_guest":      not identity["email"],
        "capped":        capped,
    }


@wc2026_router.post("/api/wc2026/board/{slug}/{difficulty}/reset")
def wc2026_reset(slug: str, difficulty: str,
                 request: Request, db: Session = Depends(get_db)):
    """Delete the board state so a fresh board is generated on next page load."""
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")
    identity = _wc_player_identity(request, db)
    row = _wc_lookup_board(db, identity, slug, difficulty)
    if row and not row.is_solved:
        db.delete(row)
        db.commit()
    return {"ok": True}


@wc2026_router.post("/api/wc2026/board/{slug}/{difficulty}/new")
def wc2026_new_game(slug: str, difficulty: str,
                    request: Request, db: Session = Depends(get_db)):
    """Generate the next random board for this player+country+difficulty after a solve."""
    if slug not in VALID_WC2026_SLUGS or difficulty not in ("easy", "hard"):
        raise HTTPException(status_code=400, detail="Invalid params")
    identity = _wc_player_identity(request, db)
    # Issue a guest token if needed — a guest "Play Again" implies a write.
    if not identity["email"] and not identity["guest_token"]:
        identity["guest_token"] = _wc_ensure_guest_token(request)

    row = _wc_lookup_board(db, identity, slug, difficulty)
    new_play_count = (getattr(row, "play_count", 0) or 0) + 1 if row else 0
    mines_json, cells_json = _make_board(
        identity["email"], slug, difficulty, new_play_count,
        guest_token=identity["guest_token"],
    )

    if row:
        row.mine_layout = mines_json
        row.cell_state  = cells_json
        row.is_solved   = False
        row.solved_at   = None
        row.play_count  = new_play_count
        row.started_at  = datetime.now(timezone.utc)
    else:
        row = WC2026BoardState(
            email=identity["email"],
            guest_token=identity["guest_token"],
            country_slug=slug, difficulty=difficulty,
            mine_layout=mines_json, cell_state=cells_json,
            is_solved=False, play_count=new_play_count,
            started_at=datetime.now(timezone.utc),
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return board_to_dict(row)


# ── API: leaderboards ─────────────────────────────────────────────────────────

@wc2026_router.get("/api/wc2026/leaderboard/countries")
def wc2026_lb_countries(db: Session = Depends(get_db), response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    return _fan_country_leaderboard(db, limit=48)


@wc2026_router.get("/api/wc2026/leaderboard/individuals")
def wc2026_lb_individuals(db: Session = Depends(get_db), response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    return _individual_leaderboard(db, limit=50)


@wc2026_router.get("/api/wc2026/leaderboard/country/{slug}")
def wc2026_lb_country(slug: str, db: Session = Depends(get_db), response: Response = None):
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    if slug not in VALID_WC2026_SLUGS:
        raise HTTPException(status_code=404)
    return _country_leaderboard(slug, db, limit=20)


# ── API: fan flag inline setter ───────────────────────────────────────────────

@wc2026_router.post("/api/wc2026/set-fan")
def wc2026_set_fan(payload: WC2026FanSet, request: Request, db: Session = Depends(get_db)):
    """Set the player's WC fan flag.

    Logged-in users: persisted to UserProfile.wc2026_fan.
    Guests: persisted to request.session["wc2026_fan"]. On later login, the
    /auth/callback merge step copies it onto the new UserProfile.
    """
    code = (payload.team or "").strip().lower() or None
    if code and code not in VALID_WC2026_SLUGS:
        return JSONResponse({"error": "Invalid team"}, status_code=400)

    user = get_current_user(request)
    if user:
        profile = db.query(UserProfile).filter(UserProfile.email == user["email"]).first()
        if not profile:
            return JSONResponse({"error": "Profile not found"}, status_code=404)
        profile.wc2026_fan = code
        db.commit()
    else:
        # Guest path — store in the signed session cookie. Issue a guest_token
        # so subsequent writes (solves, board state) carry a stable identity.
        _wc_ensure_guest_token(request)
        if code:
            request.session["wc2026_fan"] = code
        else:
            request.session.pop("wc2026_fan", None)

    return {"ok": True, "team": code,
            "country": WC2026_BY_SLUG.get(code) if code else None,
            "is_guest": not user}
