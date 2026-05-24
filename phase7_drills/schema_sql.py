"""
phase7_drills.schema_sql — DDL for the drill_sessions table.

Apply this once during deployment. The DDL is idempotent (IF NOT EXISTS).

Usage:
  python3 -m phase7_drills.schema_sql           # prints SQL to stdout
  python3 -m phase7_drills.schema_sql --apply   # connects via DATABASE_URL and applies

Why not Alembic: this project uses raw SQL migrations triggered from the
deploy script, same as game_analyses. Keeping the same pattern.
"""

from __future__ import annotations

import os
import sys


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


def main(argv: list[str]) -> int:
    if "--apply" in argv:
        try:
            from sqlalchemy import create_engine, text
        except ImportError:
            print("sqlalchemy is required for --apply", file=sys.stderr)
            return 2
        url = os.environ.get("DATABASE_URL")
        if not url:
            print("DATABASE_URL not set", file=sys.stderr)
            return 2
        engine = create_engine(url, pool_pre_ping=True)
        with engine.begin() as conn:
            conn.execute(text(DRILL_SESSIONS_DDL))
        print("Applied drill_sessions DDL")
        return 0

    print(DRILL_SESSIONS_DDL)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
