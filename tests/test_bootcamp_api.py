"""
tests/test_bootcamp_api.py — Shape, auth, and annotation-builder tests for the
bootcamp API surface.

Covers:
  Auth gate          — unauthenticated requests return 401 for every endpoint
  Response shape     — status codes for expected key fields
  Annotation builder — unit tests for _build_move_log_with_annotations
"""
import json
import os
import sys
from types import SimpleNamespace

import pytest

os.environ.setdefault("GOOGLE_CLIENT_ID",     "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SECRET_KEY",           "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("GA_TAG",               "")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# Auth gate — all bootcamp endpoints require a player identity
# ─────────────────────────────────────────────────────────────────────────────

AUTHED_ENDPOINTS = [
    ("get", "/api/bootcamp/diagnosis"),
    ("get", "/api/bootcamp/level/1/progress"),
    ("get", "/api/bootcamp/level/1"),
    ("get", "/api/radar"),
    ("get", "/api/patterns/fluency"),
    ("get", "/api/replays"),
    ("get", "/api/heatmap"),
    ("get", "/api/heatmap/cell?x=0&y=0"),
]


@pytest.mark.parametrize("method,path", AUTHED_ENDPOINTS)
def test_unauthenticated_request_returns_401(client, method, path):
    """No session cookie → player identity cannot be resolved → 401."""
    resp = getattr(client, method)(path)
    assert resp.status_code == 401, (
        f"{method.upper()} {path} returned {resp.status_code}, expected 401"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Annotation builder — pure unit tests (no HTTP, no DB)
# ─────────────────────────────────────────────────────────────────────────────

def _builder():
    from phase4_routes.routes import _build_move_log_with_annotations
    return _build_move_log_with_annotations


def _analysis(**kwargs) -> SimpleNamespace:
    """Minimal mock of a GameAnalysis SQLAlchemy row."""
    defaults = dict(
        wasted_clicks_json=None,
        shortcuts_json=None,
        openings_json=None,
        fishing_json=None,
        flag_value_json=None,
        hierarchy_deviations_json=None,
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _moves(*actions) -> list:
    """Build a raw move list as (t_ms, action_str, row, col) tuples."""
    return [(i * 100, a, 0, i) for i, a in enumerate(actions)]


def test_annotation_sequential_numbering():
    """Three wasted-click events at moves 0, 2, 4 receive annotation numbers 1, 2, 3."""
    fn = _builder()
    moves_raw = _moves("l", "r", "c", "l", "c")
    analysis = _analysis(
        wasted_clicks_json=json.dumps([
            {"move_index": 0, "reason": "safetyChord"},
            {"move_index": 2, "reason": "flagOnUnused"},
            {"move_index": 4, "reason": "safetyChord"},
        ])
    )
    move_log, annotations, _ = fn(moves_raw, analysis)
    nums = [m.annotation_number for m in move_log if m.annotation_number is not None]
    assert nums == [1, 2, 3]
    assert len(annotations) == 3
    assert [a.annotation_number for a in annotations] == [1, 2, 3]


def test_annotation_taken_opening_is_suppressed():
    """An opening the player took (positive) must not produce an annotation.
    A missed opening (taken_by_player=False) must produce annotation #1."""
    fn = _builder()
    moves_raw = _moves("l", "l")
    analysis = _analysis(
        openings_json=json.dumps([
            {"move_index": 0, "taken_by_player": True},   # positive → suppressed
            {"move_index": 1, "taken_by_player": False},  # missed → annotated
        ])
    )
    move_log, annotations, _ = fn(moves_raw, analysis)
    at_0 = next(m for m in move_log if m.move_index == 0)
    at_1 = next(m for m in move_log if m.move_index == 1)
    assert at_0.annotation_number is None
    assert at_1.annotation_number == 1
    assert len(annotations) == 1


def test_annotation_high_value_flag_is_suppressed():
    """High-value flag events (positive signal) must be suppressed; non-high-value shown."""
    fn = _builder()
    moves_raw = _moves("r", "r")
    analysis = _analysis(
        flag_value_json=json.dumps([
            {"move_index": 0, "high_value": True,  "future_chord_uses": 3, "value_score": 0.9},
            {"move_index": 1, "high_value": False, "future_chord_uses": 0, "value_score": 0.1},
        ])
    )
    move_log, annotations, _ = fn(moves_raw, analysis)
    at_0 = next(m for m in move_log if m.move_index == 0)
    at_1 = next(m for m in move_log if m.move_index == 1)
    assert at_0.annotation_number is None
    assert at_1.annotation_number == 1


def test_annotation_empty_analysis_returns_bare_moves():
    """With no JSON events every move is returned with annotation_number=None."""
    fn = _builder()
    moves_raw = _moves("l", "l", "l")
    move_log, annotations, insights = fn(moves_raw, _analysis())
    assert len(move_log) == 3
    assert all(m.annotation_number is None for m in move_log)
    assert annotations == []
    assert insights == []
