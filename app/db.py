"""SQLite access: raw SQL over stdlib sqlite3 (docs/decisions.md D18).

- `db()` opens an autocommit connection per request, inside the endpoint.
- Every mutation runs inside `tx(conn)` (BEGIN IMMEDIATE), so read-then-write
  sequences such as block moves can't interleave.
- Reads of blocks/groups go through the `live_*` views, which hide anything
  whose parent is archived (D16).
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from app.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS coaches (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    active  INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS sessions (
    id                   INTEGER PRIMARY KEY,
    date                 TEXT NOT NULL,
    start_time           TEXT NOT NULL,
    goal                 TEXT NOT NULL DEFAULT '',
    notes                TEXT NOT NULL DEFAULT '',
    shared_with_players  INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT NOT NULL,
    created_by           INTEGER REFERENCES coaches(id),
    updated_at           TEXT NOT NULL,
    updated_by           INTEGER REFERENCES coaches(id),
    archived_at          TEXT,
    archived_by          INTEGER REFERENCES coaches(id)
);

CREATE TABLE IF NOT EXISTS blocks (
    id            INTEGER PRIMARY KEY,
    session_id    INTEGER NOT NULL REFERENCES sessions(id),
    position      INTEGER NOT NULL,
    duration_min  INTEGER NOT NULL CHECK (duration_min BETWEEN 1 AND 180),
    archived_at   TEXT
);

CREATE TABLE IF NOT EXISTS activities (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT NOT NULL,
    type                  TEXT NOT NULL CHECK (type IN ('warmup', 'skill', 'game')),
    summary               TEXT NOT NULL DEFAULT '',
    tags                  TEXT NOT NULL DEFAULT '',
    description           TEXT NOT NULL DEFAULT '',
    video_url             TEXT NOT NULL DEFAULT '',
    players               TEXT NOT NULL DEFAULT '',
    coaches_needed        INTEGER,
    default_duration_min  INTEGER,
    space                 TEXT NOT NULL DEFAULT '',
    editing_by            INTEGER REFERENCES coaches(id),
    editing_since         TEXT,
    created_at            TEXT NOT NULL,
    created_by            INTEGER REFERENCES coaches(id),
    updated_at            TEXT NOT NULL,
    updated_by            INTEGER REFERENCES coaches(id),
    archived_at           TEXT,
    archived_by           INTEGER REFERENCES coaches(id)
);

CREATE TABLE IF NOT EXISTS activity_points (
    id           INTEGER PRIMARY KEY,
    activity_id  INTEGER NOT NULL REFERENCES activities(id),
    kind         TEXT NOT NULL CHECK (kind IN ('coaching', 'looks_like')),
    text         TEXT NOT NULL,
    position     INTEGER NOT NULL,
    archived_at  TEXT
);

CREATE TABLE IF NOT EXISTS activity_links (
    activity_a  INTEGER NOT NULL REFERENCES activities(id),
    activity_b  INTEGER NOT NULL REFERENCES activities(id),
    PRIMARY KEY (activity_a, activity_b),
    CHECK (activity_a < activity_b)
);

CREATE TABLE IF NOT EXISTS block_groups (
    id           INTEGER PRIMARY KEY,
    block_id     INTEGER NOT NULL REFERENCES blocks(id),
    label        TEXT NOT NULL DEFAULT '',
    activity_id  INTEGER REFERENCES activities(id),
    title        TEXT,
    why_today    TEXT NOT NULL DEFAULT '',
    how_it_went  TEXT NOT NULL DEFAULT '',
    archived_at  TEXT,
    CHECK (activity_id IS NOT NULL OR title IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS block_group_coaches (
    group_id  INTEGER NOT NULL REFERENCES block_groups(id),
    coach_id  INTEGER NOT NULL REFERENCES coaches(id),
    PRIMARY KEY (group_id, coach_id)
);

CREATE TABLE IF NOT EXISTS group_focus_points (
    id           INTEGER PRIMARY KEY,
    group_id     INTEGER NOT NULL REFERENCES block_groups(id),
    point_id     INTEGER REFERENCES activity_points(id),
    custom_text  TEXT,
    position     INTEGER NOT NULL,
    CHECK (point_id IS NOT NULL OR custom_text IS NOT NULL)
);

CREATE VIEW IF NOT EXISTS live_blocks AS
    SELECT b.* FROM blocks b
    JOIN sessions s ON s.id = b.session_id
    WHERE b.archived_at IS NULL AND s.archived_at IS NULL;

CREATE VIEW IF NOT EXISTS live_groups AS
    SELECT g.* FROM block_groups g
    JOIN live_blocks b ON b.id = g.block_id
    WHERE g.archived_at IS NULL;
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@contextmanager
def db():
    conn = sqlite3.connect(settings.db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def tx(conn: sqlite3.Connection):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    conn.execute("COMMIT")


def init_db() -> None:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    with db() as conn:
        conn.executescript(SCHEMA)


def sync_coaches(names: list[str]) -> None:
    """Add any configured coach names that aren't in the table yet (D24).

    Never removes or deactivates anyone: leavers are set `active = 0` by hand
    so their name stays on past sessions.
    """
    with db() as conn, tx(conn):
        for name in names:
            conn.execute("INSERT OR IGNORE INTO coaches (name) VALUES (?)", (name,))


def active_coaches(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT id, name FROM coaches WHERE active = 1 ORDER BY name"
    ).fetchall()
