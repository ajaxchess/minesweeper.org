"""
score_verification.py — decide whether a classic Minesweeper score may be listed
(F-MS-VERIFY, docs in intent/MinesweeperVerifiedScores.md).

A score is replayed only if it could reach a high score list. The outcome is stored
in scores.verification and every query that lists classic scores goes through
listed_scores(), so an unreplayed score can never surface.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from typing import Optional

from itsdangerous import BadSignature, URLSafeTimedSerializer
from sqlalchemy import case, func, or_

import settings as site_settings
from auth import SECRET_KEY
from database import FlaggedScore, GameMode, Score
from minesweeper_engine import ReplayError, ReplayResult, decode_board_hash, replay

# scores.verification values
VERIFIED   = "verified"     # candidate, replay succeeded
APP        = "app"          # candidate from the mobile app, no log yet (grace rule)
UNCHECKED  = "unchecked"    # not a candidate, never replayed
UNVERIFIED = "unverified"   # candidate without a usable token or log
FAILED     = "failed"       # candidate whose replay or time check failed
LISTED_STATUSES = (VERIFIED, APP)   # plus NULL: saved before this feature

GAME_TOKEN_SALT      = "minesweeper-game"
GAME_TOKEN_MAX_AGE_S = 12 * 3600
TIME_TOLERANCE_MS    = 5000   # token request latency + clock jitter

APP_CLIENT_TYPES = ("ios_app", "android_app")

# Board each fixed mode is played on (rows, cols, mines); either orientation is
# accepted because Expert has been served both as 16×30 and 30×16.
MODE_BOARDS = {
    "beginner":     (9, 9, 10),
    "intermediate": (16, 16, 40),
    "expert":       (30, 16, 99),
    "evil":         (20, 30, 130),
}
VERIFIED_MODES = ("beginner", "intermediate", "expert", "custom", "evil")

_game_tokens = URLSafeTimedSerializer(SECRET_KEY, salt=GAME_TOKEN_SALT)


def mode() -> str:
    return site_settings.SCORE_VERIFICATION_MODE


def new_game_token() -> str:
    return _game_tokens.dumps({"n": uuid.uuid4().hex})


def listed_scores(query):
    """Restrict a Score query to rows that may appear on a public list."""
    if mode() != "enforce":
        return query
    return query.filter(or_(Score.verification.is_(None), Score.verification.in_(LISTED_STATUSES)))


def _mode_value(game_mode) -> str:
    return game_mode.value if isinstance(game_mode, GameMode) else str(game_mode)


def is_candidate(db, game_mode, no_guess: bool, time_ms: int) -> bool:
    """True if fewer than SCORE_LIST_SIZE different players have a better listed
    time today. Being beaten by that many players today rules a score out of the
    daily list and of every longer period, which all contain today."""
    sort_key = case((Score.time_ms.isnot(None), Score.time_ms), else_=Score.time_secs * 1000)
    ng_filter = (Score.no_guess == True) if no_guess else (  # noqa: E712
        (Score.no_guess == False) | Score.no_guess.is_(None))  # noqa: E712
    flagged = db.query(FlaggedScore.score_id).filter(
        FlaggedScore.table_name == Score.__tablename__).scalar_subquery()
    better = listed_scores(
        db.query(func.count(func.distinct(func.coalesce(Score.user_email, Score.name))))
        .filter(Score.mode == game_mode, ng_filter, Score.created_at >= date.today(),
                ~Score.id.in_(flagged), sort_key < time_ms)
    ).scalar()
    return (better or 0) < site_settings.SCORE_LIST_SIZE


def _replay_submission(db, payload, now: datetime) -> tuple[ReplayResult, str]:
    """Replay a submission; return (result, nonce) or raise ReplayError."""
    try:
        claims, issued_at = _game_tokens.loads(
            payload.game_token, max_age=GAME_TOKEN_MAX_AGE_S, return_timestamp=True)
    except BadSignature:   # also covers an expired token
        raise ReplayError("invalid or expired game token")
    nonce = claims.get("n") if isinstance(claims, dict) else None
    if not isinstance(nonce, str) or len(nonce) != 32:
        raise ReplayError("invalid game token")
    if db.query(Score.id).filter(Score.game_nonce == nonce).first():
        raise ReplayError("game token already used")

    game_mode = _mode_value(payload.mode)
    fixed = MODE_BOARDS.get(game_mode)
    if fixed and (payload.rows, payload.cols, payload.mines) not in (
            fixed, (fixed[1], fixed[0], fixed[2])):
        raise ReplayError("board size does not match the mode")

    mines = decode_board_hash(payload.board_hash or "", payload.rows, payload.cols)
    if len(mines) != payload.mines:
        raise ReplayError("board_hash does not match the mine count")

    result = replay(payload.rows, payload.cols, mines, payload.log,
                    chording=payload.chording, evil=(game_mode == "evil"))

    if issued_at.tzinfo is None:
        issued_at = issued_at.replace(tzinfo=timezone.utc)
    elapsed_ms = (now - issued_at).total_seconds() * 1000
    if result.last_t_ms > elapsed_ms + TIME_TOLERANCE_MS:
        raise ReplayError("game claims more time than passed since it started")
    if result.last_t_ms < 1:
        raise ReplayError("game has no duration")
    return result, nonce


def verify(db, payload, client_type: str, now: Optional[datetime] = None
           ) -> tuple[Optional[str], Optional[ReplayResult], Optional[str], Optional[str]]:
    """Return (status, replay result, nonce, failure reason) for a submission.

    status is None when verification does not apply (switched off, or a mode the
    engine has no rules for), which leaves the score listed as before.
    """
    if mode() == "off" or _mode_value(payload.mode) not in VERIFIED_MODES:
        return None, None, None, None
    claimed_ms = payload.time_ms or payload.time_secs * 1000
    if not is_candidate(db, payload.mode, bool(payload.no_guess), claimed_ms):
        return UNCHECKED, None, None, None
    if not payload.game_token or not payload.log:
        if client_type in APP_CLIENT_TYPES and site_settings.SCORE_VERIFICATION_APP_GRACE:
            return APP, None, None, None
        return UNVERIFIED, None, None, "no game token or move log"
    try:
        result, nonce = _replay_submission(db, payload, now or datetime.now(timezone.utc))
    except ReplayError as exc:
        return FAILED, None, None, str(exc)
    return VERIFIED, result, nonce, None
