"""Activity library queries: cards, points, links, tags, usage and the edit lock."""

import sqlite3
from datetime import timedelta

from app.db import now_iso, tx
from app.timing import parse_iso, today_london

TYPES = {"warmup": "Warm-up", "skill": "Skill zone", "game": "Game zone", "fitness": "Fitness"}
POINT_KINDS = ("coaching", "looks_like")
LOCK_HOURS = 2

FIELDS = (
    "name", "type", "summary", "tags", "description", "video_url", "players",
    "coaches_needed", "default_duration_min", "space",
)


# --- reading ------------------------------------------------------------------


def search(conn: sqlite3.Connection, q: str = "", type_: str = "", tag: str = "") -> list[sqlite3.Row]:
    sql = "SELECT * FROM activities WHERE archived_at IS NULL"
    args: list = []
    if q:
        sql += " AND (name LIKE ? OR summary LIKE ? OR tags LIKE ? OR description LIKE ?)"
        args += [f"%{q}%"] * 4
    if type_ in TYPES:
        sql += " AND type = ?"
        args.append(type_)
    if tag:
        sql += " AND (',' || tags || ',') LIKE ?"
        args.append(f"%,{tag},%")
    sql += " ORDER BY name COLLATE NOCASE"
    return conn.execute(sql, args).fetchall()


def get(conn: sqlite3.Connection, activity_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT a.*, u.name AS updated_by_name, e.name AS editing_by_name
           FROM activities a
           LEFT JOIN coaches u ON u.id = a.updated_by
           LEFT JOIN coaches e ON e.id = a.editing_by
           WHERE a.id = ?""",
        (activity_id,),
    ).fetchone()


def points(conn: sqlite3.Connection, activity_id: int) -> dict[str, list[sqlite3.Row]]:
    rows = conn.execute(
        """SELECT id, kind, text FROM activity_points
           WHERE activity_id = ? AND archived_at IS NULL ORDER BY position, id""",
        (activity_id,),
    ).fetchall()
    return {kind: [r for r in rows if r["kind"] == kind] for kind in POINT_KINDS}


def all_tags(conn: sqlite3.Connection) -> list[str]:
    tags: set[str] = set()
    for (value,) in conn.execute("SELECT tags FROM activities WHERE archived_at IS NULL"):
        tags.update(t for t in value.split(",") if t)
    return sorted(tags)


def related(conn: sqlite3.Connection, activity_id: int) -> list[sqlite3.Row]:
    """Linked activities, from either side of the pair (one row per link)."""
    return conn.execute(
        """SELECT a.id, a.name, a.type FROM activity_links l
           JOIN activities a ON a.id = CASE WHEN l.activity_a = ? THEN l.activity_b ELSE l.activity_a END
           WHERE (l.activity_a = ? OR l.activity_b = ?) AND a.archived_at IS NULL
           ORDER BY a.name COLLATE NOCASE""",
        (activity_id, activity_id, activity_id),
    ).fetchall()


def usage(conn: sqlite3.Connection, activity_id: int) -> dict:
    """'Run N× · last <date>' plus notes from past sessions (D11)."""
    today = today_london().isoformat()
    stats = conn.execute(
        """SELECT COUNT(DISTINCT s.id) AS runs, MAX(s.date) AS last
           FROM live_groups g
           JOIN blocks b ON b.id = g.block_id
           JOIN sessions s ON s.id = b.session_id
           WHERE g.activity_id = ? AND s.date <= ?""",
        (activity_id, today),
    ).fetchone()
    notes = conn.execute(
        """SELECT s.id AS session_id, s.date, g.how_it_went,
                  (SELECT group_concat(c.name, ' & ') FROM block_group_coaches gc
                   JOIN coaches c ON c.id = gc.coach_id WHERE gc.group_id = g.id) AS coaches
           FROM live_groups g
           JOIN blocks b ON b.id = g.block_id
           JOIN sessions s ON s.id = b.session_id
           WHERE g.activity_id = ? AND s.date <= ? AND trim(g.how_it_went) != ''
           ORDER BY s.date DESC""",
        (activity_id, today),
    ).fetchall()
    return {"runs": stats["runs"], "last": stats["last"], "notes": notes}


def sessions_using(conn: sqlite3.Connection, activity_id: int) -> int:
    return conn.execute(
        """SELECT COUNT(DISTINCT b.session_id) FROM live_groups g
           JOIN blocks b ON b.id = g.block_id WHERE g.activity_id = ?""",
        (activity_id,),
    ).fetchone()[0]


# --- edit lock (D17) -----------------------------------------------------------


def lock_holder(activity: sqlite3.Row, coach_id: int) -> str | None:
    """Name of someone *else* holding a live lock, or None if you may edit."""
    if activity["editing_by"] is None or activity["editing_by"] == coach_id:
        return None
    if lock_expired(activity):
        return None
    return activity["editing_by_name"]


def lock_expired(activity: sqlite3.Row) -> bool:
    since = parse_iso(activity["editing_since"])
    return since + timedelta(hours=LOCK_HOURS) < parse_iso(now_iso())


def take_lock(conn: sqlite3.Connection, activity_id: int, coach_id: int) -> bool:
    with tx(conn):
        activity = get(conn, activity_id)
        if activity is None or lock_holder(activity, coach_id):
            return False
        conn.execute(
            "UPDATE activities SET editing_by = ?, editing_since = ? WHERE id = ?",
            (coach_id, now_iso(), activity_id),
        )
    return True


def release_lock(conn: sqlite3.Connection, activity_id: int, coach_id: int) -> None:
    with tx(conn):
        conn.execute(
            "UPDATE activities SET editing_by = NULL, editing_since = NULL WHERE id = ? AND editing_by = ?",
            (activity_id, coach_id),
        )


# --- writing -------------------------------------------------------------------


def create(conn: sqlite3.Connection, values: dict, point_rows: dict, coach_id: int | None) -> int:
    now = now_iso()
    with tx(conn):
        cur = conn.execute(
            f"""INSERT INTO activities ({', '.join(FIELDS)}, created_at, created_by, updated_at, updated_by)
                VALUES ({', '.join('?' * len(FIELDS))}, ?, ?, ?, ?)""",
            [values[f] for f in FIELDS] + [now, coach_id, now, coach_id],
        )
        activity_id = cur.lastrowid
        _save_points(conn, activity_id, point_rows)
    return activity_id


def update(conn: sqlite3.Connection, activity_id: int, values: dict, point_rows: dict, coach_id: int) -> str | None:
    """Save an edit if this coach still holds the lock.

    Returns None on success, or the name of whoever took the lock over.
    """
    with tx(conn):
        activity = get(conn, activity_id)
        if activity["editing_by"] != coach_id:
            return activity["editing_by_name"] or "someone else"
        conn.execute(
            f"""UPDATE activities SET {', '.join(f + ' = ?' for f in FIELDS)},
                updated_at = ?, updated_by = ?, editing_by = NULL, editing_since = NULL
                WHERE id = ?""",
            [values[f] for f in FIELDS] + [now_iso(), coach_id, activity_id],
        )
        _save_points(conn, activity_id, point_rows)
    return None


def _save_points(conn: sqlite3.Connection, activity_id: int, point_rows: dict) -> None:
    """Apply the edited point lists: update kept rows, insert new, archive removed (D7)."""
    existing = {
        r["id"] for r in conn.execute(
            "SELECT id FROM activity_points WHERE activity_id = ? AND archived_at IS NULL",
            (activity_id,),
        )
    }
    kept: set[int] = set()
    for kind in POINT_KINDS:
        for position, (point_id, text) in enumerate(point_rows.get(kind, [])):
            if point_id in existing:
                kept.add(point_id)
                conn.execute(
                    "UPDATE activity_points SET text = ?, position = ? WHERE id = ?",
                    (text, position, point_id),
                )
            else:
                conn.execute(
                    "INSERT INTO activity_points (activity_id, kind, text, position) VALUES (?, ?, ?, ?)",
                    (activity_id, kind, text, position),
                )
    for point_id in existing - kept:
        conn.execute("UPDATE activity_points SET archived_at = ? WHERE id = ?", (now_iso(), point_id))


def set_archived(conn: sqlite3.Connection, activity_id: int, archived: bool, coach_id: int) -> None:
    with tx(conn):
        if archived:
            conn.execute(
                "UPDATE activities SET archived_at = ?, archived_by = ? WHERE id = ? AND archived_at IS NULL",
                (now_iso(), coach_id, activity_id),
            )
        else:
            conn.execute(
                "UPDATE activities SET archived_at = NULL, archived_by = NULL WHERE id = ?",
                (activity_id,),
            )


def link(conn: sqlite3.Connection, a: int, b: int) -> None:
    if a == b:
        return
    with tx(conn):
        conn.execute(
            "INSERT OR IGNORE INTO activity_links (activity_a, activity_b) VALUES (?, ?)",
            (min(a, b), max(a, b)),
        )


def unlink(conn: sqlite3.Connection, a: int, b: int) -> None:
    with tx(conn):
        conn.execute(
            "DELETE FROM activity_links WHERE activity_a = ? AND activity_b = ?",
            (min(a, b), max(a, b)),
        )
