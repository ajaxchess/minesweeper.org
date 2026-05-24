"""
phase7_drills.smoke_test — exercise the drill routes against an in-memory
SQLite DB + FastAPI TestClient.

Runs against stubbed auth/limiter (no project imports needed).

Usage:
    python3 phase7_drills/smoke_test.py
"""

from __future__ import annotations

import sys
import os

# Make sure we import from the parent dir
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def run() -> int:
    try:
        from fastapi import FastAPI, Request
        from fastapi.testclient import TestClient
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
    except ImportError as e:
        print(f"Skipping smoke test — missing dep: {e}")
        return 0

    # Build an isolated engine + session
    # SQLite doesn't know about MEDIUMTEXT (mysql-only). Register a compiler
    # that just emits "TEXT" so create_all() works for the test DB.
    from sqlalchemy.dialects.mysql import MEDIUMTEXT
    from sqlalchemy.ext.compiler import compiles
    @compiles(MEDIUMTEXT, "sqlite")
    def _sqlite_mediumtext(_type, _compiler, **_kw):
        return "TEXT"

    from phase7_drills.models import Base, DrillSession  # noqa
    from sqlalchemy.pool import StaticPool
    # StaticPool keeps a single sqlite :memory: connection, so all sessions
    # see the same tables.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    # Set up the FastAPI app with dependency overrides
    from phase7_drills import routes as drill_routes
    def _test_get_db():
        s = SessionLocal()
        try:
            yield s
        finally:
            s.close()

    def _test_player(_request: Request):
        return {"email": "smoketest@example.com"}

    # The routes call get_current_user directly (not via Depends), so we have
    # to monkey-patch it. get_db IS used via Depends, so override that.
    drill_routes.get_current_user = _test_player

    app = FastAPI()
    app.include_router(drill_routes.api_router)
    app.dependency_overrides[drill_routes.get_db] = _test_get_db

    client = TestClient(app)

    # 1) Start a drill with only 3 boards for speed
    r = client.post("/api/drills/start", json={
        "drill_type": "l5_opening_recognition",
        "level": 5,
        "difficulty": "expert",
        "mode": "standard",
        "num_boards": 3,
    })
    assert r.status_code == 200, (r.status_code, r.text)
    start = r.json()
    drill_id = start["drill_id"]
    assert len(start["boards"]) == 3
    for b in start["boards"]:
        assert b["width"] == 30 and b["height"] == 16
        assert len(b["revealed"]) > 0
    print(f"✓ Start: drill_id={drill_id}, boards={len(start['boards'])}")

    # 2) Submit one cell for each board. We deliberately mix in the optimal
    #    cell sometimes and a random cell other times by reading the stored
    #    solution from the DB (test-only).
    with SessionLocal() as s:
        drill = s.get(DrillSession, drill_id)
        import json
        solutions = json.loads(drill.boards_json)

    for idx, sol in enumerate(solutions):
        if idx == 0:
            # Click the optimal cell — should score correct
            r, c = sol["optimal_cell"]
        elif idx == 1:
            # Click a mine — should score is_mine=True, correct=False
            r, c = sol["mines"][0]
        else:
            # Click some safe unrevealed cell not in correct_cells — wrong
            mines = {tuple(m) for m in sol["mines"]}
            revealed = {tuple(p) for p in sol["revealed"]}
            correct = {tuple(p) for p in sol["correct_cells"]}
            candidate = None
            for rr in range(sol["height"]):
                for cc in range(sol["width"]):
                    if (rr, cc) in mines: continue
                    if (rr, cc) in revealed: continue
                    if (rr, cc) in correct: continue
                    candidate = (rr, cc)
                    break
                if candidate: break
            assert candidate is not None, "No suboptimal cell found"
            r, c = candidate

        resp = client.post(f"/api/drills/{drill_id}/submit", json={
            "board_index": idx,
            "chosen_row": r,
            "chosen_col": c,
            "decision_ms": 1500 + idx * 500,
        })
        assert resp.status_code == 200, (resp.status_code, resp.text)
        payload = resp.json()
        verdict = payload["result"]
        if idx == 0:
            assert verdict["is_correct"] is True,  "Optimal cell should be correct"
            assert verdict["is_mine"]    is False
        elif idx == 1:
            assert verdict["is_mine"]    is True,  "Mine click should be flagged"
            assert verdict["is_correct"] is False
        else:
            assert verdict["is_correct"] is False, "Suboptimal cell should be wrong"
            assert verdict["is_mine"]    is False

    # 3) Last submit should have completed=True and a summary
    assert payload["completed"] is True
    summary = payload["summary"]
    assert summary["num_total"] == 3
    assert summary["num_correct"] == 1
    assert summary["counted_toward_mastery"] is True
    assert 0.0 < summary["mastery_contribution"] <= 1.0
    print(f"✓ All 3 submits OK · correct={summary['num_correct']}/3 · "
          f"mastery={summary['mastery_contribution']:.3f}")

    # 4) Re-submitting a board is idempotent
    r2 = client.post(f"/api/drills/{drill_id}/submit", json={
        "board_index": 0,
        "chosen_row": 0, "chosen_col": 0,
        "decision_ms": 100,
    })
    # The drill is already completed, so a brand-new submit returns 409
    assert r2.status_code == 409, (r2.status_code, r2.text)
    print("✓ Re-submitting a completed drill returns 409")

    # 5) Refresh the drill state — should match summary
    state = client.get(f"/api/drills/{drill_id}").json()
    assert state["completed_at"] is not None
    assert len(state["attempts"]) == 3
    print(f"✓ State refresh: attempts={len(state['attempts'])}")

    # 6) Wrong owner gets 404
    drill_routes.get_current_user = lambda _r: {"email": "intruder@example.com"}
    r3 = client.get(f"/api/drills/{drill_id}")
    assert r3.status_code == 404
    print("✓ Wrong owner gets 404")

    print("\nALL SMOKE TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(run())
