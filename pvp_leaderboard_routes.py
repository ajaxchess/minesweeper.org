"""
pvp_leaderboard_routes.py — Leaderboard and rankings API endpoints for PvP.
Mount this router in main.py with: app.include_router(pvp_leaderboard_router)

Core PvP/duel game routes live in duel_routes.py.
These are the leaderboard and player-card API endpoints.
"""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Request, Depends, Query, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import (
    UserProfile, PvpResult, GameHistory,
    get_db,
)
from auth import get_current_user
from translations import SUPPORTED_LANGS
import settings as site_settings
from quest_catalog import quest_config
from breadcrumbs import get_breadcrumbs as _get_breadcrumbs

pvp_leaderboard_router = APIRouter()

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
templates.env.globals["ga_tag"]               = ""
templates.env.globals["get_breadcrumbs"]      = _get_breadcrumbs


# ── Season helpers (mirrors of main.py; no circular-import solution) ──────────

SEASON_ORIGIN_YEAR  = 2026
SEASON_ORIGIN_MONTH = 3  # March


def get_season_range(season_num: int):
    """Return (start_date, end_date) for the given 1-based season number."""
    total = SEASON_ORIGIN_MONTH - 1 + (season_num - 1)
    year  = SEASON_ORIGIN_YEAR + total // 12
    month = total % 12 + 1
    start = date(year, month, 1)
    end   = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def current_season_num() -> int:
    today = date.today()
    return (today.year - SEASON_ORIGIN_YEAR) * 12 + (today.month - SEASON_ORIGIN_MONTH) + 1


def get_period_range(period: str, target: Optional[date] = None, season_num: Optional[int] = None):
    """Return date bounds for finite leaderboard periods."""
    target = target or date.today()
    if period == "daily":
        return target, target + timedelta(days=1)
    if period == "weekly":
        start = target - timedelta(days=target.weekday())
        return start, start + timedelta(days=7)
    if period == "monthly":
        start = target.replace(day=1)
        end = date(start.year + 1, 1, 1) if start.month == 12 else date(start.year, start.month + 1, 1)
        return start, end
    if period == "yearly":
        start = date(target.year, 1, 1)
        return start, date(target.year + 1, 1, 1)
    if period == "season":
        return get_season_range(season_num) if season_num and season_num >= 1 else get_season_range(current_season_num())
    return None, None


# ── PvP Leaderboard & Rankings API ───────────────────────────────────────────

@pvp_leaderboard_router.get("/api/pvp/leaderboard")
def get_pvp_leaderboard(period: str = "alltime",
                        score_date: Optional[str] = Query(None, alias="date"),
                        season_num: Optional[int] = Query(None),
                        submode: Optional[str] = Query(None),
                        db: Session = Depends(get_db),
                        response: Response = None):
    """Return best PvP games ranked by winner's time (fastest first)."""
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"
    if period not in ("daily", "weekly", "monthly", "season", "yearly", "alltime"):
        period = "alltime"

    q = db.query(PvpResult)
    if submode in ("standard", "quick"):
        q = q.filter(PvpResult.submode == submode)

    if period in ("daily", "weekly", "monthly", "season", "yearly"):
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        p_start, p_end = get_period_range(period, target, season_num)
        q = q.filter(PvpResult.created_at >= p_start,
                     PvpResult.created_at < p_end)
        if period == "daily":
            rows = q.order_by(PvpResult.elapsed_ms.asc()).limit(15).all()
            return [r.to_dict() for r in rows]

    # Best game per winner (dedup by winner_email or winner_name)
    raw = q.order_by(PvpResult.elapsed_ms.asc()).limit(500).all()
    seen: set = set()
    top: list = []
    for r in raw:
        key = r.winner_email or r.winner_name or str(r.id)
        if key not in seen:
            seen.add(key)
            top.append(r.to_dict())
            if len(top) >= 15:
                break
    return top


@pvp_leaderboard_router.get("/api/pvp/rankings")
def get_pvp_rankings(period: str = "alltime",
                     score_date: Optional[str] = Query(None, alias="date"),
                     season_num: Optional[int] = Query(None),
                     submode: Optional[str] = Query(None),
                     db: Session = Depends(get_db),
                     response: Response = None):
    """Return players ranked by number of PvP wins."""
    if period not in ("daily", "weekly", "monthly", "season", "yearly", "alltime"):
        period = "alltime"
    if response:
        response.headers["Cache-Control"] = "public, max-age=60"

    q = db.query(PvpResult)
    if submode in ("standard", "quick"):
        q = q.filter(PvpResult.submode == submode)

    if period in ("daily", "weekly", "monthly", "season", "yearly"):
        try:
            target = date.fromisoformat(score_date) if score_date else date.today()
        except ValueError:
            target = date.today()
        p_start, p_end = get_period_range(period, target, season_num)
        q = q.filter(PvpResult.created_at >= p_start,
                     PvpResult.created_at < p_end)

    rows = q.all()

    # Count wins per player
    wins: dict = {}
    for r in rows:
        key   = r.winner_email or r.winner_name or "Anonymous"
        label = r.winner_name  or "Anonymous"
        if key not in wins:
            wins[key] = {"name": label, "email": r.winner_email, "wins": 0}
        wins[key]["wins"] += 1

    ranked = sorted(wins.values(), key=lambda x: x["wins"], reverse=True)
    top = ranked[:15]

    # Attach Elo rating and public profile URL for each ranked player
    emails = [p["email"] for p in top if p.get("email")]
    if emails:
        profiles = db.query(UserProfile).filter(UserProfile.email.in_(emails)).all()
        profile_map = {p.email: p for p in profiles}
        for p in top:
            prof = profile_map.get(p.get("email"))
            p["elo"]     = prof.pvp_elo if prof else None
            p["country"] = prof.country if prof else None
            if prof and prof.is_public:
                p["profile_url"] = f"/u/{prof.vanity_slug or prof.public_id}"
            else:
                p["profile_url"] = None

    return top


@pvp_leaderboard_router.get("/api/pvp/elo-rankings")
def get_pvp_elo_rankings(db: Session = Depends(get_db), response: Response = None):
    """Return players ranked by Elo rating (only players who have played at least one match)."""
    if response:
        response.headers["Cache-Control"] = "public, max-age=300"
    winner_emails = db.query(PvpResult.winner_email).filter(PvpResult.winner_email != None)
    loser_emails  = db.query(PvpResult.loser_email ).filter(PvpResult.loser_email  != None)
    played_emails = {row[0] for row in winner_emails.union(loser_emails).all()}
    if not played_emails:
        return []
    profiles = (
        db.query(UserProfile)
        .filter(UserProfile.email.in_(played_emails))
        .order_by(UserProfile.pvp_elo.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "name":        p.display_name,
            "elo":         p.pvp_elo,
            "country":     p.country,
            "profile_url": f"/u/{p.vanity_slug or p.public_id}" if p.is_public else None,
        }
        for p in profiles
    ]


@pvp_leaderboard_router.get("/api/pvp/player-card/{public_id}")
def pvp_player_card(public_id: str, db: Session = Depends(get_db)):
    """Lightweight stat card data for the PvP match header mouseover (F69)."""
    profile = db.query(UserProfile).filter(UserProfile.public_id == public_id).first()
    if not profile:
        return {}
    best_expert = (
        db.query(func.min(GameHistory.time_secs))
        .filter(GameHistory.user_email == profile.email, GameHistory.mode == "expert")
        .scalar()
    )
    wins   = db.query(func.count(PvpResult.id)).filter(PvpResult.winner_email == profile.email).scalar() or 0
    losses = db.query(func.count(PvpResult.id)).filter(PvpResult.loser_email  == profile.email).scalar() or 0
    return {
        "name":      profile.display_name,
        "elo":       profile.pvp_elo,
        "wins":      wins,
        "losses":    losses,
        "best_time": best_expert,
    }
