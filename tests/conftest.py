"""
tests/conftest.py — pytest fixtures for minesweeper.org

Sets up an in-memory SQLite database so tests run without a MySQL server.
Overrides FastAPI's get_db dependency with a SQLite-backed session.
"""
import os
import sys
import shutil
import hashlib
import pytest

# ── Dummy env vars required by auth.py before any app import ──────────────────
os.environ.setdefault("GOOGLE_CLIENT_ID",     "test-client-id.apps.googleusercontent.com")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("SECRET_KEY",           "test-secret-key-32-chars-minimum!!")
os.environ.setdefault("GA_TAG",               "")
# Disable slowapi rate limiting so tests can POST freely without hitting limits
os.environ["RATELIMIT_ENABLED"] = "0"

# ── Ensure project root is on the path ────────────────────────────────────────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# ── Create database.py from template if missing (local dev without MySQL) ─────
DB_PY       = os.path.join(ROOT, "database.py")
TEMPLATE_PY = os.path.join(ROOT, "database_template.py")
if not os.path.exists(DB_PY):
    shutil.copy(TEMPLATE_PY, DB_PY)

# ── Patch the database module to use SQLite in-memory ─────────────────────────
# Must happen before main.py is imported so that init_db() uses SQLite.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import database as _db

# StaticPool: all sessions share one in-memory connection so tables created
# by init_db() are visible to every subsequent session in the same process.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_db.engine       = _test_engine
_db.SessionLocal = sessionmaker(bind=_test_engine, autocommit=False, autoflush=False)

# _apply_migrations() uses MySQL information_schema — skip it in tests.
_db._apply_migrations = lambda: None

# ── Import the app after patching ─────────────────────────────────────────────
from main import app, get_db  # noqa: E402
from fastapi.testclient import TestClient

# ── Override get_db to use the SQLite session factory ─────────────────────────
def _override_get_db():
    db = _db.SessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

# ── Shared TestClient (session-scoped: one app startup per test run) ──────────
@pytest.fixture(scope="session")
def client():
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

# ── Helper: standard CSRF header required by all POST /api/* routes ───────────
XHR = {"X-Requested-With": "XMLHttpRequest"}

# ── Per-test DB cleanup: truncate all rows after each test ────────────────────
@pytest.fixture(autouse=True)
def clean_db():
    yield
    db = _db.SessionLocal()
    try:
        for table in reversed(_db.Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()

# ── Utility: compute board_id the same way the server does ───────────────────
def board_id(rows: int, cols: int, board_hash: str, board_mask: str = "") -> str:
    raw = f"{rows}x{cols}:{board_hash}:{board_mask}"
    return hashlib.sha256(raw.encode()).hexdigest()
