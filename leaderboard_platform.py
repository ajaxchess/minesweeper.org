"""Normalized leaderboard catalog and query layer.

This module gives the leaderboard page one data contract across games that
store scores in different historical tables. The UI can ask for cards or a
single full board without knowing which score table backs each game.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Literal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from database import (
    CubesweeperScore,
    CylinderScore,
    FifteenPuzzleScore,
    FlaggedScore,
    Game2048HexScore,
    Game2048Score,
    GlobesweeperScore,
    HexsweeperScore,
    JigsawScore,
    MahjongScore,
    MobiussweeperScore,
    MosaicEasyScore,
    MosaicScore,
    NonosweeperScore,
    NumbersMatchScore,
    PvpResult,
    RushScore,
    SchulteGridScore,
    Score,
    SudokuScore,
    TametsiScore,
    TentaizuEasyScore,
    TentaizuScore,
    ToroidScore,
    UserProfile,
    WC2026Score,
)
from wc2026_data import WC2026_COUNTRIES


Period = Literal["daily", "weekly", "monthly", "season", "yearly", "alltime"]
Metric = Literal["time", "score", "wins"]

SUPPORTED_PERIODS: tuple[Period, ...] = ("daily", "weekly", "monthly", "season", "yearly", "alltime")
SEASON_ORIGIN_YEAR = 2026
SEASON_ORIGIN_MONTH = 3


@dataclass(frozen=True)
class LeaderboardSpec:
    id: str
    title: str
    category: str
    group: str
    play_href: str
    full_href: str
    model: Any
    metric: Metric
    popularity: int
    level_label: str | None = None
    filters: tuple[tuple[str, Any], ...] = ()
    date_string_field: str | None = None
    mode_field: str | None = None
    rank_field: str | None = None
    name_field: str = "name"
    email_field: str = "user_email"
    board_label_fields: tuple[str, ...] = ()
    note: str | None = None


def _season_range(season_num: int | None) -> tuple[date, date]:
    num = season_num if season_num and season_num >= 1 else _current_season_num()
    total = SEASON_ORIGIN_MONTH - 1 + (num - 1)
    year = SEASON_ORIGIN_YEAR + total // 12
    month = total % 12 + 1
    start = date(year, month, 1)
    end = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return start, end


def _current_season_num() -> int:
    today = date.today()
    return (today.year - SEASON_ORIGIN_YEAR) * 12 + (today.month - SEASON_ORIGIN_MONTH) + 1


def _period_range(period: str, target: date, season_num: int | None) -> tuple[date | None, date | None]:
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
        return _season_range(season_num)
    return None, None


def _mode_value(value: str) -> Any:
    # Score.mode is an Enum column, but SQLAlchemy accepts the stored string for filters.
    return value


LEADERBOARD_SPECS: tuple[LeaderboardSpec, ...] = (
    LeaderboardSpec("classic-beginner", "Classic Beginner", "minesweeper", "Classic", "/", "/leaderboard?game=classic&mode=beginner", Score, "time", 10, "Beginner", (("mode", _mode_value("beginner")), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("classic-intermediate", "Classic Intermediate", "minesweeper", "Classic", "/intermediate", "/leaderboard?game=classic&mode=intermediate", Score, "time", 20, "Intermediate", (("mode", _mode_value("intermediate")), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("classic-expert", "Classic Expert", "minesweeper", "Classic", "/expert", "/leaderboard?game=classic&mode=expert", Score, "time", 30, "Expert", (("mode", _mode_value("expert")), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("classic-custom", "Classic Custom", "minesweeper", "Classic", "/custom", "/leaderboard?game=classic&mode=custom", Score, "time", 40, "Custom", (("mode", _mode_value("custom")), ("no_guess", False)), rank_field="time", board_label_fields=("rows", "cols", "mines")),
    LeaderboardSpec("classic-evil-ng", "Evil No-Guess", "minesweeper", "Classic", "/evil", "/leaderboard?game=classic&mode=evil&no_guess=true", Score, "time", 50, "Evil NG", (("mode", _mode_value("evil")), ("no_guess", True)), rank_field="time"),
    LeaderboardSpec("cylinder-easy", "Cylinder Easy", "minesweeper", "Cylinder", "/cylinder", "/leaderboard?game=cylinder&mode=easy", CylinderScore, "time", 60, "Easy", (("cyl_mode", "easy"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("cylinder-intermediate", "Cylinder Intermediate", "minesweeper", "Cylinder", "/cylinder/intermediate", "/leaderboard?game=cylinder&mode=intermediate", CylinderScore, "time", 70, "Intermediate", (("cyl_mode", "intermediate"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("cylinder-expert", "Cylinder Expert", "minesweeper", "Cylinder", "/cylinder/expert", "/leaderboard?game=cylinder&mode=expert", CylinderScore, "time", 80, "Expert", (("cyl_mode", "expert"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("toroid-easy", "Toroid Easy", "minesweeper", "Toroid", "/toroid", "/leaderboard?game=toroid&mode=easy", ToroidScore, "time", 90, "Easy", (("tor_mode", "easy"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("toroid-intermediate", "Toroid Intermediate", "minesweeper", "Toroid", "/toroid/intermediate", "/leaderboard?game=toroid&mode=intermediate", ToroidScore, "time", 100, "Intermediate", (("tor_mode", "intermediate"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("toroid-expert", "Toroid Expert", "minesweeper", "Toroid", "/toroid/expert", "/leaderboard?game=toroid&mode=expert", ToroidScore, "time", 110, "Expert", (("tor_mode", "expert"), ("no_guess", False)), rank_field="time"),
    LeaderboardSpec("hex-beginner", "Hexsweeper Easy", "minesweeper", "Hexsweeper", "/hexsweeper", "/leaderboard?game=hex&mode=beginner", HexsweeperScore, "time", 120, "Easy", (("hex_mode", "beginner"),), rank_field="time", board_label_fields=("radius", "mines")),
    LeaderboardSpec("hex-intermediate", "Hexsweeper Intermediate", "minesweeper", "Hexsweeper", "/hexsweeper/intermediate", "/leaderboard?game=hex&mode=intermediate", HexsweeperScore, "time", 130, "Intermediate", (("hex_mode", "intermediate"),), rank_field="time", board_label_fields=("radius", "mines")),
    LeaderboardSpec("hex-expert", "Hexsweeper Expert", "minesweeper", "Hexsweeper", "/hexsweeper/expert", "/leaderboard?game=hex&mode=expert", HexsweeperScore, "time", 140, "Expert", (("hex_mode", "expert"),), rank_field="time", board_label_fields=("radius", "mines")),
    LeaderboardSpec("worldsweeper", "Worldsweeper", "minesweeper", "Worldsweeper", "/worldsweeper", "/worldsweeper/leaderboard", GlobesweeperScore, "time", 150, "Beginner", (("glob_mode", "beginner"),), rank_field="time"),
    LeaderboardSpec("cubesweeper", "Cubesweeper", "minesweeper", "Cubesweeper", "/cubesweeper", "/cubesweeper/leaderboard", CubesweeperScore, "time", 160, "Beginner", (("cube_mode", "beginner"),), rank_field="time"),
    LeaderboardSpec("mobiussweeper", "Mobiussweeper", "minesweeper", "Mobiussweeper", "/mobiussweeper", "/mobiussweeper/leaderboard", MobiussweeperScore, "time", 170, "Beginner", (("mobius_mode", "beginner"),), rank_field="time"),
    LeaderboardSpec("nonosweeper-beginner", "Nonosweeper Beginner", "minesweeper", "Nonosweeper", "/nonosweeper", "/nonosweeper#nn-lb-section", NonosweeperScore, "time", 180, "Beginner", (("difficulty", "beginner"),), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("rush-easy", "Rush Easy", "rush", "Rush", "/rush", "/rush/leaderboard", RushScore, "score", 190, "Easy", (("rush_mode", "easy"),), rank_field="score"),
    LeaderboardSpec("rush-normal", "Rush Normal", "rush", "Rush", "/rush", "/rush/leaderboard", RushScore, "score", 200, "Normal", (("rush_mode", "normal"),), rank_field="score"),
    LeaderboardSpec("rush-hard", "Rush Hard", "rush", "Rush", "/rush", "/rush/leaderboard", RushScore, "score", 210, "Hard", (("rush_mode", "hard"),), rank_field="score"),
    LeaderboardSpec("tentaizu-daily", "Tentaizu Daily", "puzzles", "Tentaizu", "/puzzles/tentaizu", "/puzzles/tentaizu#tz-lb-section", TentaizuScore, "time", 300, "Daily", date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("tentaizu-easy", "Tentaizu Easy", "puzzles", "Tentaizu", "/puzzles/tentaizu/easy-5x5-6", "/puzzles/tentaizu/easy-5x5-6#tz-lb-section", TentaizuEasyScore, "time", 310, "Easy", date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("mosaic-daily", "Mosaic Daily", "puzzles", "Mosaic", "/puzzles/mosaic", "/puzzles/mosaic#ms-lb-section", MosaicScore, "time", 320, "Daily", date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("mosaic-easy", "Mosaic Easy", "puzzles", "Mosaic", "/puzzles/mosaic/easy", "/puzzles/mosaic/easy#ms-lb-section", MosaicEasyScore, "time", 330, "Easy", date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("tametsi-beginner", "Tametsi Beginner", "puzzles", "Tametsi", "/puzzles/tametsi", "/puzzles/tametsi#tmt-lb-section", TametsiScore, "time", 340, "Beginner", (("level", "beginner"), ("is_daily", True)), rank_field="time"),
    LeaderboardSpec("numbers-match", "Numbers Match", "puzzles", "Numbers Match", "/puzzles/numbers-match", "/puzzles/numbers-match#nm-lb-section", NumbersMatchScore, "score", 350, "Daily", date_string_field="puzzle_date", rank_field="score"),
    LeaderboardSpec("15-puzzle", "15-Puzzle", "puzzles", "15-Puzzle", "/puzzles/15-puzzle", "/puzzles/15-puzzle/leaderboard", FifteenPuzzleScore, "time", 360, "4x4", (("grid_size", "4x4"),), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("2048", "2048", "puzzles", "2048", "/puzzles/2048", "/puzzles/2048/leaderboard", Game2048Score, "score", 370, "Daily", date_string_field="puzzle_date", rank_field="score"),
    LeaderboardSpec("2048-hexagon", "2048 Hexagon", "puzzles", "2048 Hexagon", "/puzzles/2048-hexagon", "/puzzles/2048-hexagon/leaderboard", Game2048HexScore, "score", 380, "Daily", date_string_field="puzzle_date", rank_field="score"),
    LeaderboardSpec("mahjong-solitaire", "Mahjong Solitaire", "puzzles", "Mahjong", "/puzzles/mahjong-solitaire", "/puzzles/mahjong-solitaire/leaderboard", MahjongScore, "time", 390, "Daily", date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("jigsaw-beginner", "Jigsaw Beginner", "puzzles", "Jigsaw", "/puzzles/jigsaw", "/puzzles/jigsaw/leaderboard", JigsawScore, "time", 400, "Beginner", (("difficulty", "beginner"),), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("jigsaw-intermediate", "Jigsaw Intermediate", "puzzles", "Jigsaw", "/puzzles/jigsaw", "/puzzles/jigsaw/leaderboard", JigsawScore, "time", 410, "Intermediate", (("difficulty", "intermediate"),), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("jigsaw-expert", "Jigsaw Expert", "puzzles", "Jigsaw", "/puzzles/jigsaw", "/puzzles/jigsaw/leaderboard", JigsawScore, "time", 420, "Expert", (("difficulty", "expert"),), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("schulte-grid", "Schulte Grid", "puzzles", "Schulte", "/puzzles/schulte-grid", "/puzzles/schulte-grid/leaderboard", SchulteGridScore, "time", 430, "Normal 5x5", (("mode", "normal"), ("board_size", 5)), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("sudoku-daily", "Sudoku Daily", "puzzles", "Sudoku", "/puzzles/sudoku", "/puzzles/sudoku/leaderboard", SudokuScore, "time", 440, "Daily", (("difficulty", "daily"), ("variant", "standard")), date_string_field="puzzle_date", rank_field="time"),
    LeaderboardSpec("pvp-wins", "PvP Wins", "pvp", "PvP", "/pvp", "/pvp/rankings", PvpResult, "wins", 490, "Wins", name_field="winner_name", email_field="winner_email"),
    LeaderboardSpec("pvp-best-times", "PvP Best Times", "pvp", "PvP", "/pvp", "/pvp/leaderboard", PvpResult, "time", 500, "Best Times", rank_field="time", name_field="winner_name", email_field="winner_email"),
    LeaderboardSpec("wc2026-individuals", "World Cup 2026 Individuals", "events", "World Cup 2026", "/2026worldcup", "/2026worldcup", WC2026Score, "score", 600, "Individuals"),
    LeaderboardSpec("wc2026-countries", "World Cup 2026 Countries", "events", "World Cup 2026", "/2026worldcup", "/2026worldcup", WC2026Score, "score", 610, "Countries"),
)

SPECS_BY_ID: dict[str, LeaderboardSpec] = {spec.id: spec for spec in LEADERBOARD_SPECS}
WC2026_BY_SLUG = {country["slug"]: country for country in WC2026_COUNTRIES}


def leaderboard_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": spec.id,
            "title": spec.title,
            "category": spec.category,
            "group": spec.group,
            "level": spec.level_label,
            "metric": spec.metric,
            "play_href": spec.play_href,
            "full_href": spec.full_href,
            "popularity": spec.popularity,
        }
        for spec in sorted(LEADERBOARD_SPECS, key=lambda s: s.popularity)
    ]


def _exclude_flagged(query, model, db: Session):
    flagged_ids = (
        select(FlaggedScore.score_id)
        .where(FlaggedScore.table_name == model.__tablename__)
    )
    return query.filter(~model.id.in_(flagged_ids))


def _apply_period(query, spec: LeaderboardSpec, period: Period, target: date, season_num: int | None):
    if period == "alltime":
        return query
    if period == "daily" and spec.date_string_field:
        return query.filter(getattr(spec.model, spec.date_string_field) == target.isoformat())
    start, end = _period_range(period, target, season_num)
    if start and end:
        return query.filter(spec.model.created_at >= start, spec.model.created_at < end)
    return query


def _rank_expression(spec: LeaderboardSpec):
    if spec.metric == "score":
        return getattr(spec.model, "score")
    if spec.model is Score:
        return case((Score.time_ms.isnot(None), Score.time_ms), else_=Score.time_secs * 1000)
    if hasattr(spec.model, "time_ms"):
        return getattr(spec.model, "time_ms")
    if hasattr(spec.model, "elapsed_ms"):
        return getattr(spec.model, "elapsed_ms")
    return getattr(spec.model, "time_secs") * 1000


def _order_query(query, spec: LeaderboardSpec):
    rank_expr = _rank_expression(spec)
    if spec.metric == "score" or spec.metric == "wins":
        return query.order_by(rank_expr.desc(), spec.model.created_at.asc())
    return query.order_by(rank_expr.asc(), spec.model.created_at.asc())


def _profile_maps(rows: list[Any], spec: LeaderboardSpec, db: Session):
    emails = [getattr(row, spec.email_field, None) for row in rows if getattr(row, spec.email_field, None)]
    if not emails:
        return {}, {}
    profiles = (
        db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id, UserProfile.is_public, UserProfile.country)
        .filter(UserProfile.email.in_(emails))
        .all()
    )
    urls: dict[str, str] = {}
    countries: dict[str, str] = {}
    for profile in profiles:
        if profile.country:
            countries[profile.email] = profile.country
        if profile.is_public:
            urls[profile.email] = f"/u/{profile.vanity_slug or profile.public_id}"
    return urls, countries


def _metric_value(row: Any, spec: LeaderboardSpec) -> int | float | None:
    if spec.metric == "score":
        return getattr(row, "score", None)
    value = _rank_expression(spec)
    try:
        # When rank expression is a real SQL expression, compute from row fields.
        if spec.model is Score:
            return row.time_ms if row.time_ms is not None else row.time_secs * 1000
    except AttributeError:
        pass
    if hasattr(row, "time_ms"):
        return row.time_ms
    if hasattr(row, "elapsed_ms"):
        return row.elapsed_ms
    if hasattr(row, "time_secs"):
        return row.time_secs * 1000
    return None


def _board_label(row: Any, spec: LeaderboardSpec) -> str | None:
    if "rows" in spec.board_label_fields and "cols" in spec.board_label_fields:
        return f"{getattr(row, 'rows', '?')}x{getattr(row, 'cols', '?')} / {getattr(row, 'mines', '?')} mines"
    if "radius" in spec.board_label_fields:
        return f"R{getattr(row, 'radius', '?')} / {getattr(row, 'mines', '?')} mines"
    if hasattr(row, "board_hash") and getattr(row, "board_hash", None):
        return str(getattr(row, "board_hash"))[:10]
    return None


def _row_dict(row: Any, spec: LeaderboardSpec, rank: int, urls: dict[str, str], countries: dict[str, str]) -> dict[str, Any]:
    email = getattr(row, spec.email_field, None)
    return {
        "rank": rank,
        "name": getattr(row, spec.name_field, None) or "Anonymous",
        "profile_url": urls.get(email) if email else None,
        "country": countries.get(email) if email else None,
        "metric": spec.metric,
        "metric_value": _metric_value(row, spec),
        "created_at": row.created_at.strftime("%Y-%m-%d") if getattr(row, "created_at", None) else None,
        "board": _board_label(row, spec),
    }


def _profile_maps_for_emails(emails: list[str], db: Session) -> tuple[dict[str, str], dict[str, str]]:
    if not emails:
        return {}, {}
    profiles = (
        db.query(UserProfile.email, UserProfile.vanity_slug, UserProfile.public_id, UserProfile.is_public, UserProfile.country)
        .filter(UserProfile.email.in_(emails))
        .all()
    )
    urls: dict[str, str] = {}
    countries: dict[str, str] = {}
    for profile in profiles:
        if profile.country:
            countries[profile.email] = profile.country
        if profile.is_public:
            urls[profile.email] = f"/u/{profile.vanity_slug or profile.public_id}"
    return urls, countries


def _pvp_win_rows(
    db: Session,
    spec: LeaderboardSpec,
    *,
    period: Period,
    target: date,
    season_num: int | None,
    limit: int,
) -> dict[str, Any]:
    query = db.query(PvpResult)
    query = _apply_period(query, spec, period, target, season_num)
    rows = query.all()
    wins: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = row.winner_email or row.winner_name or f"guest-{row.id}"
        if key not in wins:
            wins[key] = {"name": row.winner_name or "Anonymous", "email": row.winner_email, "wins": 0}
        wins[key]["wins"] += 1

    ranked = sorted(wins.values(), key=lambda item: (-item["wins"], item["name"].lower()))[:limit]
    urls, countries = _profile_maps_for_emails([row["email"] for row in ranked if row.get("email")], db)
    return {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "group": spec.group,
        "level": spec.level_label,
        "period": period,
        "metric": spec.metric,
        "play_href": spec.play_href,
        "full_href": spec.full_href,
        "rows": [
            {
                "rank": index + 1,
                "name": row["name"],
                "profile_url": urls.get(row["email"]) if row.get("email") else None,
                "country": countries.get(row["email"]) if row.get("email") else None,
                "metric": spec.metric,
                "metric_value": row["wins"],
                "created_at": None,
                "board": "Wins",
            }
            for index, row in enumerate(ranked)
        ],
    }


def _wc2026_individual_rows(db: Session, spec: LeaderboardSpec, *, limit: int) -> dict[str, Any]:
    rows = (
        db.query(
            WC2026Score.email,
            WC2026Score.display_name,
            WC2026Score.fan_flag,
            func.sum(WC2026Score.total_points).label("points"),
        )
        .group_by(WC2026Score.email, WC2026Score.display_name, WC2026Score.fan_flag)
        .order_by(func.sum(WC2026Score.total_points).desc(), func.min(WC2026Score.solve_time_ms).asc())
        .limit(limit)
        .all()
    )
    urls, countries = _profile_maps_for_emails([row.email for row in rows if row.email], db)
    return {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "group": spec.group,
        "level": spec.level_label,
        "period": "alltime",
        "metric": spec.metric,
        "play_href": spec.play_href,
        "full_href": spec.full_href,
        "rows": [
            {
                "rank": index + 1,
                "name": row.display_name or "Anonymous",
                "profile_url": urls.get(row.email),
                "country": countries.get(row.email) or row.fan_flag,
                "metric": spec.metric,
                "metric_value": int(row.points or 0),
                "created_at": None,
                "board": "World Cup 2026",
            }
            for index, row in enumerate(rows)
        ],
    }


def _wc2026_country_rows(db: Session, spec: LeaderboardSpec, *, limit: int) -> dict[str, Any]:
    rows = (
        db.query(
            WC2026Score.fan_flag,
            func.sum(WC2026Score.total_points).label("points"),
        )
        .group_by(WC2026Score.fan_flag)
        .order_by(func.sum(WC2026Score.total_points).desc())
        .limit(limit)
        .all()
    )
    return {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "group": spec.group,
        "level": spec.level_label,
        "period": "alltime",
        "metric": spec.metric,
        "play_href": spec.play_href,
        "full_href": spec.full_href,
        "rows": [
            {
                "rank": index + 1,
                "name": WC2026_BY_SLUG.get(row.fan_flag, {}).get("name", row.fan_flag),
                "profile_url": None,
                "country": WC2026_BY_SLUG.get(row.fan_flag, {}).get("flag", row.fan_flag),
                "metric": spec.metric,
                "metric_value": int(row.points or 0),
                "created_at": None,
                "board": "Team points",
            }
            for index, row in enumerate(rows)
        ],
    }


def leaderboard_rows(
    db: Session,
    leaderboard_id: str,
    *,
    period: str = "daily",
    target: date | None = None,
    season_num: int | None = None,
    limit: int = 15,
) -> dict[str, Any]:
    spec = SPECS_BY_ID.get(leaderboard_id)
    if not spec:
        raise KeyError(leaderboard_id)
    clean_period: Period = period if period in SUPPORTED_PERIODS else "daily"  # type: ignore[assignment]
    target_date = target or date.today()

    if spec.id == "pvp-wins":
        return _pvp_win_rows(db, spec, period=clean_period, target=target_date, season_num=season_num, limit=limit)
    if spec.id == "wc2026-individuals":
        return _wc2026_individual_rows(db, spec, limit=limit)
    if spec.id == "wc2026-countries":
        return _wc2026_country_rows(db, spec, limit=limit)

    query = db.query(spec.model)
    for field, value in spec.filters:
        query = query.filter(getattr(spec.model, field) == value)
    query = _apply_period(query, spec, clean_period, target_date, season_num)
    query = _exclude_flagged(query, spec.model, db)
    query = _order_query(query, spec)

    raw = query.limit(max(limit * 12, 60)).all()
    seen: set[str] = set()
    rows: list[Any] = []
    for row in raw:
        key = getattr(row, spec.email_field, None) or getattr(row, spec.name_field, None) or str(getattr(row, "id"))
        if key in seen:
            continue
        seen.add(key)
        rows.append(row)
        if len(rows) >= limit:
            break

    urls, countries = _profile_maps(rows, spec, db)
    return {
        "id": spec.id,
        "title": spec.title,
        "category": spec.category,
        "group": spec.group,
        "level": spec.level_label,
        "period": clean_period,
        "metric": spec.metric,
        "play_href": spec.play_href,
        "full_href": spec.full_href,
        "rows": [_row_dict(row, spec, index + 1, urls, countries) for index, row in enumerate(rows)],
    }


def leaderboard_cards(
    db: Session,
    *,
    period: str = "daily",
    category: str = "all",
    target: date | None = None,
    season_num: int | None = None,
    limit: int = 3,
) -> list[dict[str, Any]]:
    specs = sorted(LEADERBOARD_SPECS, key=lambda s: s.popularity)
    if category != "all":
        specs = [spec for spec in specs if spec.category == category]
    return [
        leaderboard_rows(db, spec.id, period=period, target=target, season_num=season_num, limit=limit)
        for spec in specs
    ]


def leaderboard_summary(db: Session) -> dict[str, Any]:
    counts = []
    for spec in sorted(LEADERBOARD_SPECS, key=lambda s: s.popularity):
        query = db.query(func.count(spec.model.id))
        for field, value in spec.filters:
            query = query.filter(getattr(spec.model, field) == value)
        counts.append({"id": spec.id, "count": int(query.scalar() or 0), "popularity": spec.popularity})
    return {"leaderboards": counts}
