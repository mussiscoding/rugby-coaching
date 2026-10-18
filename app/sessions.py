"""Session queries: sessions → blocks → groups, plus coaches and focus points.

Blocks and groups are read through the live_* views (D16). Every block or group
change bumps the session's updated_at/by, which drives "Last edited by" (D17).
"""

import sqlite3

from app.db import now_iso, tx
from app.timing import today_london


# --- reading --------------------------------------------------------------------


def list_sessions(conn: sqlite3.Connection) -> dict[str, list[sqlite3.Row]]:
    today = today_london().isoformat()
    rows = conn.execute(
        """SELECT s.*, (SELECT COUNT(*) FROM live_blocks b WHERE b.session_id = s.id) AS block_count
           FROM sessions s WHERE s.archived_at IS NULL ORDER BY s.date, s.start_time"""
    ).fetchall()
    return {
        "upcoming": [r for r in rows if r["date"] >= today],
        "past": [r for r in reversed(rows) if r["date"] < today],
    }


def get_session(conn: sqlite3.Connection, session_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT s.*, u.name AS updated_by_name FROM sessions s
           LEFT JOIN coaches u ON u.id = s.updated_by WHERE s.id = ?""",
        (session_id,),
    ).fetchone()


def load(conn: sqlite3.Connection, session_id: int) -> list[dict]:
    """The session's live blocks, each with its live groups, in order."""
    blocks = [
        dict(b) | {"groups": []}
        for b in conn.execute(
            "SELECT * FROM live_blocks WHERE session_id = ? ORDER BY position, id", (session_id,)
        )
    ]
    by_id = {b["id"]: b for b in blocks}
    if not blocks:
        return blocks
    marks = ",".join("?" * len(by_id))
    groups = conn.execute(
        f"""SELECT g.*, a.name AS activity_name, a.type AS activity_type, a.summary AS activity_summary,
                   a.archived_at AS activity_archived_at
            FROM live_groups g LEFT JOIN activities a ON a.id = g.activity_id
            WHERE g.block_id IN ({marks}) ORDER BY g.id""",
        list(by_id),
    ).fetchall()
    group_ids = [g["id"] for g in groups]
    coaches = _by_group(conn, group_ids, """
        SELECT gc.group_id, c.id, c.name FROM block_group_coaches gc
        JOIN coaches c ON c.id = gc.coach_id WHERE gc.group_id IN ({marks}) ORDER BY c.name""")
    focus = _by_group(conn, group_ids, """
        SELECT f.group_id, f.point_id, COALESCE(p.text, f.custom_text) AS text
        FROM group_focus_points f LEFT JOIN activity_points p ON p.id = f.point_id
        WHERE f.group_id IN ({marks}) ORDER BY f.position""")
    for g in groups:
        by_id[g["block_id"]]["groups"].append(
            dict(g) | {"coaches": coaches.get(g["id"], []), "focus": focus.get(g["id"], [])}
        )
    return blocks


def _by_group(conn, group_ids: list[int], sql: str) -> dict[int, list[sqlite3.Row]]:
    if not group_ids:
        return {}
    out: dict[int, list[sqlite3.Row]] = {}
    for row in conn.execute(sql.format(marks=",".join("?" * len(group_ids))), group_ids):
        out.setdefault(row["group_id"], []).append(row)
    return out


def get_group(conn: sqlite3.Connection, group_id: int) -> sqlite3.Row | None:
    return conn.execute(
        """SELECT g.*, b.session_id, b.id AS block_id, s.date AS session_date,
                  a.name AS activity_name, a.archived_at AS activity_archived_at
           FROM live_groups g
           JOIN blocks b ON b.id = g.block_id
           JOIN sessions s ON s.id = b.session_id
           LEFT JOIN activities a ON a.id = g.activity_id
           WHERE g.id = ?""",
        (group_id,),
    ).fetchone()


def get_block(conn: sqlite3.Connection, block_id: int) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM live_blocks WHERE id = ?", (block_id,)).fetchone()


def group_coach_ids(conn, group_id: int) -> set[int]:
    return {r[0] for r in conn.execute("SELECT coach_id FROM block_group_coaches WHERE group_id = ?", (group_id,))}


def group_focus(conn, group_id: int) -> tuple[set[int], list[str]]:
    """(starred activity point ids, session-only point texts)."""
    rows = conn.execute(
        "SELECT point_id, custom_text FROM group_focus_points WHERE group_id = ? ORDER BY position", (group_id,)
    ).fetchall()
    return {r["point_id"] for r in rows if r["point_id"]}, [r["custom_text"] for r in rows if not r["point_id"]]


def used_labels(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute(
        "SELECT label FROM block_groups WHERE label != '' GROUP BY label ORDER BY COUNT(*) DESC LIMIT 30"
    )]


def previous_activity_ids(conn: sqlite3.Connection, session_id: int, before_block_id: int | None) -> list[int]:
    """Activities in the last block (or the block before `before_block_id`)."""
    blocks = [b["id"] for b in conn.execute(
        "SELECT id FROM live_blocks WHERE session_id = ? ORDER BY position, id", (session_id,))]
    if before_block_id in blocks:
        blocks = blocks[: blocks.index(before_block_id) + 1]
    if not blocks:
        return []
    return [r[0] for r in conn.execute(
        "SELECT activity_id FROM live_groups WHERE block_id = ? AND activity_id IS NOT NULL", (blocks[-1],))]


# --- writing --------------------------------------------------------------------


def touch(conn, session_id: int, coach_id: int) -> None:
    conn.execute("UPDATE sessions SET updated_at = ?, updated_by = ? WHERE id = ?", (now_iso(), coach_id, session_id))


def create_session(conn, date: str, start_time: str, goal: str, coach_id: int) -> int:
    now = now_iso()
    with tx(conn):
        cur = conn.execute(
            """INSERT INTO sessions (date, start_time, goal, created_at, created_by, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (date, start_time, goal, now, coach_id, now, coach_id),
        )
    return cur.lastrowid


def update_session(conn, session_id: int, values: dict, coach_id: int) -> None:
    with tx(conn):
        conn.execute(
            "UPDATE sessions SET date = ?, start_time = ?, goal = ?, notes = ? WHERE id = ?",
            (values["date"], values["start_time"], values["goal"], values["notes"], session_id),
        )
        touch(conn, session_id, coach_id)


def add_block(conn, session_id: int, duration: int, activity_id: int | None, title: str | None, coach_id: int) -> int:
    with tx(conn):
        position = conn.execute(
            "SELECT COALESCE(MAX(position), 0) + 1 FROM blocks WHERE session_id = ?", (session_id,)
        ).fetchone()[0]
        block_id = conn.execute(
            "INSERT INTO blocks (session_id, position, duration_min) VALUES (?, ?, ?)",
            (session_id, position, duration),
        ).lastrowid
        conn.execute(
            "INSERT INTO block_groups (block_id, activity_id, title) VALUES (?, ?, ?)",
            (block_id, activity_id, title),
        )
        touch(conn, session_id, coach_id)
    return block_id


def add_group(conn, block: sqlite3.Row, activity_id: int | None, title: str | None, coach_id: int) -> int:
    with tx(conn):
        group_id = conn.execute(
            "INSERT INTO block_groups (block_id, activity_id, title) VALUES (?, ?, ?)",
            (block["id"], activity_id, title),
        ).lastrowid
        touch(conn, block["session_id"], coach_id)
    return group_id


def set_duration(conn, block: sqlite3.Row, duration: int, coach_id: int) -> None:
    with tx(conn):
        conn.execute("UPDATE blocks SET duration_min = ? WHERE id = ?", (duration, block["id"]))
        touch(conn, block["session_id"], coach_id)


def move_block(conn, block: sqlite3.Row, direction: str, coach_id: int) -> None:
    """Swap with the nearest live neighbour (archived blocks leave gaps)."""
    with tx(conn):
        siblings = [r["id"] for r in conn.execute(
            "SELECT id FROM live_blocks WHERE session_id = ? ORDER BY position, id", (block["session_id"],))]
        i = siblings.index(block["id"])
        j = i - 1 if direction == "up" else i + 1
        if 0 <= j < len(siblings):
            siblings[i], siblings[j] = siblings[j], siblings[i]
            for position, block_id in enumerate(siblings, start=1):
                conn.execute("UPDATE blocks SET position = ? WHERE id = ?", (position, block_id))
            touch(conn, block["session_id"], coach_id)


def save_group(conn, group: sqlite3.Row, values: dict, coach_ids: list[int],
               point_ids: list[int], custom_points: list[str], coach_id: int) -> None:
    with tx(conn):
        conn.execute(
            "UPDATE block_groups SET label = ?, title = ?, why_today = ?, how_it_went = ? WHERE id = ?",
            (values["label"], values["title"], values["why_today"], values["how_it_went"], group["id"]),
        )
        conn.execute("DELETE FROM block_group_coaches WHERE group_id = ?", (group["id"],))
        for cid in coach_ids:
            conn.execute("INSERT INTO block_group_coaches (group_id, coach_id) VALUES (?, ?)", (group["id"], cid))
        conn.execute("DELETE FROM group_focus_points WHERE group_id = ?", (group["id"],))
        position = 0
        for pid in point_ids:
            conn.execute(
                "INSERT INTO group_focus_points (group_id, point_id, position) VALUES (?, ?, ?)",
                (group["id"], pid, position),
            )
            position += 1
        for text in custom_points:
            conn.execute(
                "INSERT INTO group_focus_points (group_id, custom_text, position) VALUES (?, ?, ?)",
                (group["id"], text, position),
            )
            position += 1
        touch(conn, group["session_id"], coach_id)


def set_archived(conn, table: str, row_id: int, session_id: int, archived: bool, coach_id: int) -> None:
    """Archive/restore a block or group. A restored block goes to the end (D16)."""
    assert table in ("blocks", "block_groups")
    with tx(conn):
        if archived:
            conn.execute(f"UPDATE {table} SET archived_at = ? WHERE id = ?", (now_iso(), row_id))
        else:
            conn.execute(f"UPDATE {table} SET archived_at = NULL WHERE id = ?", (row_id,))
            if table == "blocks":
                conn.execute(
                    """UPDATE blocks SET position =
                       (SELECT COALESCE(MAX(position), 0) + 1 FROM blocks WHERE session_id = ?) WHERE id = ?""",
                    (session_id, row_id),
                )
        touch(conn, session_id, coach_id)


def set_session_archived(conn, session_id: int, archived: bool, coach_id: int) -> None:
    with tx(conn):
        if archived:
            conn.execute(
                "UPDATE sessions SET archived_at = ?, archived_by = ? WHERE id = ?", (now_iso(), coach_id, session_id))
        else:
            conn.execute("UPDATE sessions SET archived_at = NULL, archived_by = NULL WHERE id = ?", (session_id,))


def copy_session(conn, source_id: int, new_date: str, coach_id: int) -> int:
    """Copy a session's plan to a new date (D12).

    Copied: goal, start time, blocks, groups, coaches, why today, starred points.
    Cleared: how it went, session notes, share-with-players.
    """
    source = get_session(conn, source_id)
    now = now_iso()
    with tx(conn):
        new_id = conn.execute(
            """INSERT INTO sessions (date, start_time, goal, created_at, created_by, updated_at, updated_by)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (new_date, source["start_time"], source["goal"], now, coach_id, now, coach_id),
        ).lastrowid
        blocks = conn.execute(
            "SELECT * FROM live_blocks WHERE session_id = ? ORDER BY position, id", (source_id,)).fetchall()
        for position, block in enumerate(blocks, start=1):
            block_id = conn.execute(
                "INSERT INTO blocks (session_id, position, duration_min) VALUES (?, ?, ?)",
                (new_id, position, block["duration_min"]),
            ).lastrowid
            for g in conn.execute("SELECT * FROM live_groups WHERE block_id = ? ORDER BY id", (block["id"],)).fetchall():
                group_id = conn.execute(
                    """INSERT INTO block_groups (block_id, label, activity_id, title, why_today)
                       VALUES (?, ?, ?, ?, ?)""",
                    (block_id, g["label"], g["activity_id"], g["title"], g["why_today"]),
                ).lastrowid
                conn.execute(
                    """INSERT INTO block_group_coaches (group_id, coach_id)
                       SELECT ?, coach_id FROM block_group_coaches WHERE group_id = ?""",
                    (group_id, g["id"]),
                )
                conn.execute(
                    """INSERT INTO group_focus_points (group_id, point_id, custom_text, position)
                       SELECT ?, point_id, custom_text, position FROM group_focus_points WHERE group_id = ?""",
                    (group_id, g["id"]),
                )
    return new_id


def recently_deleted(conn) -> list[dict]:
    """Only the topmost deleted thing: a block inside a deleted session isn't listed separately."""
    rows = []
    for r in conn.execute("SELECT id, date, goal, archived_at FROM sessions WHERE archived_at IS NOT NULL"):
        rows.append({"kind": "session", "id": r["id"], "what": f"Session · {r['date']}", "detail": r["goal"],
                     "archived_at": r["archived_at"], "restore": f"/sessions/{r['id']}/restore", "session_id": r["id"]})
    for r in conn.execute("SELECT id, name, archived_at FROM activities WHERE archived_at IS NOT NULL"):
        rows.append({"kind": "activity", "id": r["id"], "what": "Activity", "detail": r["name"],
                     "archived_at": r["archived_at"], "restore": f"/activities/{r['id']}/restore", "session_id": None})
    for r in conn.execute(
        """SELECT b.id, b.archived_at, s.id AS session_id, s.date,
                  (SELECT group_concat(COALESCE(a.name, g.title), ' / ') FROM block_groups g
                   LEFT JOIN activities a ON a.id = g.activity_id WHERE g.block_id = b.id AND g.archived_at IS NULL) AS names
           FROM blocks b JOIN sessions s ON s.id = b.session_id
           WHERE b.archived_at IS NOT NULL AND s.archived_at IS NULL"""):
        rows.append({"kind": "block", "id": r["id"], "what": f"Block · session {r['date']}", "detail": r["names"] or "",
                     "archived_at": r["archived_at"], "restore": f"/blocks/{r['id']}/restore", "session_id": r["session_id"]})
    for r in conn.execute(
        """SELECT g.id, g.archived_at, g.label, COALESCE(a.name, g.title) AS name, b.session_id, s.date
           FROM block_groups g JOIN live_blocks b ON b.id = g.block_id JOIN sessions s ON s.id = b.session_id
           LEFT JOIN activities a ON a.id = g.activity_id WHERE g.archived_at IS NOT NULL"""):
        detail = f"{r['label']}: {r['name']}" if r["label"] else r["name"]
        rows.append({"kind": "group", "id": r["id"], "what": f"Group · session {r['date']}", "detail": detail,
                     "archived_at": r["archived_at"], "restore": f"/groups/{r['id']}/restore", "session_id": r["session_id"]})
    return sorted(rows, key=lambda r: r["archived_at"], reverse=True)
