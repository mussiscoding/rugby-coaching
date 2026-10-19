"""What players are allowed to see. This is the security boundary (D15).

Player templates only ever receive the output of `player_projection()`: a plain
dict built from an allowlist of fields. Coach names, coaching points,
descriptions, progressions, "how it went" and session notes are never copied
in, so no template change can leak them by accident.
"""

from app.timing import layout, today_london


def visible_to_players(session) -> bool:
    return (
        session is not None
        and session["archived_at"] is None
        and bool(session["shared_with_players"])
        and session["date"] >= today_london().isoformat()
    )


def player_projection(session, blocks: list[dict]) -> dict:
    plan = layout([b["duration_min"] for b in blocks], session["start_time"])
    return {
        "id": session["id"],
        "date": session["date"],
        "start_time": session["start_time"],
        "end": plan["end"],
        "total": plan["total"],
        "goal": session["goal"],
        "blocks": [
            {
                "clock_start": t["clock_start"],
                "clock_end": t["clock_end"],
                "minutes": b["duration_min"],
                "split": len(b["groups"]) > 1,
                "groups": [
                    {
                        "label": g["label"],
                        "name": g["activity_name"] or g["title"] or "",
                        "type": g["activity_type"],
                        "why": g["why_today"],
                    }
                    for g in b["groups"]
                ],
            }
            for b, t in zip(blocks, plan["blocks"])
        ],
    }
