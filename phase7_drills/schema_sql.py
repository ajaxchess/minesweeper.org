"""
phase7_drills.schema_sql — DDL for the drill_sessions table.

Apply this once during deployment. The DDL is idempotent (IF NOT EXISTS).

Usage:
  python3 phase7_drills/schema_sql.py                # prints SQL to stdout
  python3 phase7_drills/schema_sql.py --apply        # connects via:
                                                       #   1) project's `database.engine` (or main.engine)
                                                       #   2) .env in cwd / parent / script dir
                                                       #   3) os.environ
                                                       # whichever resolves first

To pipe directly into the mysql CLI (no Python deps beyond stdlib):
  python3 phase7_drills/schema_sql.py | mysql -u <user> -p <database>

NOTE: run as a script path, NOT `python3 -m phase7_drills.schema_sql`. The
`-m` form triggers __init__.py which would import FastAPI; this script only
needs SQLAlchemy (and only for --apply).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


DRILL_SESSIONS_DDL = """
CREATE TABLE IF NOT EXISTS drill_sessions (
    id                       INT NOT NULL AUTO_INCREMENT,
    player_id                VARCHAR(256) NOT NULL,
    drill_type               VARCHAR(64)  NOT NULL,
    level                    INT          NOT NULL,
    difficulty               VARCHAR(16)  NOT NULL DEFAULT 'expert',
    mode                     VARCHAR(16)  NOT NULL DEFAULT 'standard',
    num_boards               INT          NOT NULL DEFAULT 10,

    boards_json              MEDIUMTEXT   NOT NULL,
    attempts_json            MEDIUMTEXT   NOT NULL,

    started_at               DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at             DATETIME     NULL,

    num_correct              INT          NULL,
    avg_decision_ms          INT          NULL,
    mastery_contribution     FLOAT        NULL,
    counted_toward_mastery   TINYINT(1)   NOT NULL DEFAULT 0,

    drill_version            VARCHAR(16)  NOT NULL DEFAULT '1.0',

    PRIMARY KEY (id),
    INDEX ix_drill_sessions_player_started (player_id, started_at),
    INDEX ix_drill_sessions_player_level   (player_id, level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
""".strip()


# Variable names we'll look for in .env / os.environ when assembling the
# connection string. We try the most explicit ones first.
URL_KEYS  = ("DATABASE_URL", "MYSQL_URL", "DB_URL", "SQLALCHEMY_DATABASE_URI")
HOST_KEYS = ("DB_HOST", "MYSQL_HOST", "DATABASE_HOST")
PORT_KEYS = ("DB_PORT", "MYSQL_PORT", "DATABASE_PORT")
USER_KEYS = ("DB_USER", "MYSQL_USER", "DATABASE_USER", "DB_USERNAME", "MYSQL_USERNAME")
PASS_KEYS = ("DB_PASSWORD", "MYSQL_PASSWORD", "DATABASE_PASSWORD", "DB_PASS", "MYSQL_PASS")
NAME_KEYS = ("DB_NAME", "MYSQL_DATABASE", "DATABASE_NAME", "MYSQL_DB", "DB_DATABASE")


def _load_dotenv_files() -> dict:
    """Read .env from a few sensible locations and return a dict.

    Does NOT overwrite values already in os.environ.

    Locations searched, in order:
      - $PWD/.env
      - <script-dir>/../.env  (i.e. project root if script lives in pkg dir)
      - $HOME/.env (last resort)
    """
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path.home() / ".env",
    ]
    out: dict = {}
    for path in candidates:
        try:
            if not path.exists():
                continue
        except OSError:
            continue
        for raw in path.read_text(errors="replace").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export "):]
            if "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if k and k not in out:
                out[k] = v
        # Use only the first .env we find — keeps precedence deterministic.
        break
    return out


def _first(d: dict, keys: tuple) -> Optional[str]:
    for k in keys:
        if d.get(k):
            return d[k]
    return None


def _build_url(env: dict) -> Optional[str]:
    """Construct a SQLAlchemy URL from env vars."""
    explicit = _first(env, URL_KEYS)
    if explicit:
        # If they wrote a bare mysql:// URL, upgrade to mysql+pymysql:// so
        # SQLAlchemy doesn't try to load MySQLdb (which isn't installed in
        # most modern deploys).
        if explicit.startswith("mysql://"):
            return "mysql+pymysql://" + explicit[len("mysql://"):]
        return explicit

    user = _first(env, USER_KEYS)
    host = _first(env, HOST_KEYS) or "localhost"
    name = _first(env, NAME_KEYS)
    if not user or not name:
        return None
    pw   = _first(env, PASS_KEYS) or ""
    port = _first(env, PORT_KEYS) or "3306"
    from urllib.parse import quote_plus
    cred = quote_plus(user) + (":" + quote_plus(pw) if pw else "")
    return f"mysql+pymysql://{cred}@{host}:{port}/{name}"


def _resolve_env() -> dict:
    """Merge .env values into a copy of os.environ (os.environ wins)."""
    merged = dict(_load_dotenv_files())
    merged.update(os.environ)  # process env overrides .env
    return merged


def _get_engine():
    """Return a SQLAlchemy Engine, or raise RuntimeError with a useful hint."""
    # 1) project's `database.engine`
    try:
        from database import engine                          # type: ignore
        if engine is not None:
            return engine
    except Exception:
        pass

    # 2) main.engine (last-resort; may pull in FastAPI — fine for --apply)
    try:
        from main import engine                              # type: ignore
        if engine is not None:
            return engine
    except Exception:
        pass

    # 3) Assemble URL from .env / process env
    env = _resolve_env()
    url = _build_url(env)
    if url:
        from sqlalchemy import create_engine
        return create_engine(url, pool_pre_ping=True)

    keys_we_tried = (URL_KEYS, HOST_KEYS, PORT_KEYS, USER_KEYS, PASS_KEYS, NAME_KEYS)
    flat = sorted({k for group in keys_we_tried for k in group})
    raise RuntimeError(
        "Could not assemble a database URL.\n"
        "\n"
        "Tried these resolution paths in order:\n"
        "  1. `from database import engine` (project's shared engine)\n"
        "  2. `from main import engine`\n"
        "  3. .env in $PWD / project root / $HOME, then process env\n"
        "\n"
        "Looked for any of: " + ", ".join(flat) + "\n"
        "\n"
        "Workaround — pipe the DDL straight into the mysql CLI:\n"
        "    python3 phase7_drills/schema_sql.py | mysql -u <user> -p <database>"
    )


def main(argv: list[str]) -> int:
    if "--show-env" in argv:
        # Diagnostic: dump which keys we found (values masked).
        env = _resolve_env()
        flat = set()
        for group in (URL_KEYS, HOST_KEYS, PORT_KEYS, USER_KEYS, PASS_KEYS, NAME_KEYS):
            flat.update(group)
        for k in sorted(flat):
            v = env.get(k)
            if v:
                mask = v if k in HOST_KEYS or k in PORT_KEYS or k in NAME_KEYS else "***"
                print(f"  {k} = {mask}")
            else:
                print(f"  {k} = (not set)")
        return 0

    if "--apply" in argv:
        try:
            from sqlalchemy import text
        except ImportError:
            print("sqlalchemy is required for --apply", file=sys.stderr)
            return 2
        try:
            engine = _get_engine()
        except RuntimeError as e:
            print(str(e), file=sys.stderr)
            return 2
        with engine.begin() as conn:
            conn.execute(text(DRILL_SESSIONS_DDL))
        print("Applied drill_sessions DDL")
        return 0

    print(DRILL_SESSIONS_DDL)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
