"""Player-view redaction: the security boundary (D15).

Every coach-only field gets a unique marker; none may appear anywhere in the
player's HTML (text, attributes or links).
"""

import re
from datetime import timedelta

from app.db import db
from app.timing import today_london

COACH_ONLY = ["ZZCOACHNAME", "ZZSUMMARY", "ZZDESC", "ZZPROGRESSION", "ZZCOACHPOINT", "ZZLOOKS",
              "ZZTAG", "ZZSPACE", "ZZPLAYERS", "zzvideo", "ZZCUSTOMPOINT", "ZZHOW", "ZZNOTES"]


def _session(coach_client, days_ahead=7):
    date = (today_london() + timedelta(days=days_ahead)).isoformat()
    r = coach_client.post("/sessions", data={"date": date, "start_time": "18:30", "goal": "Visible goal"})
    return int(r.headers["location"].rsplit("/", 1)[1])


def _build(coach_client):
    with db() as conn:
        conn.execute("UPDATE coaches SET name = 'ZZCOACHNAME' || id")
    r = coach_client.post("/activities", data={
        "name": "Visible activity", "type": "skill", "summary": "ZZSUMMARY", "tags": "ZZTAG",
        "description": "## How to run\nZZDESC\n## Progressions\n- ZZPROGRESSION\n",
        "players": "ZZPLAYERS", "space": "ZZSPACE", "video_url": "https://zzvideo.example/x",
        "coaching_id": [""], "coaching_text": ["ZZCOACHPOINT"], "looks_like_id": [""], "looks_like_text": ["ZZLOOKS"],
    })
    activity_id = r.headers["location"].rsplit("/", 1)[1]
    sid = _session(coach_client)
    coach_client.post(f"/sessions/{sid}/blocks", data={"activity_id": activity_id, "duration": "20"})
    group_id = re.search(r'href="/groups/(\d+)"', coach_client.get(f"/sessions/{sid}").text).group(1)
    point_id = re.search(r'name="point_id" value="(\d+)"', coach_client.get(f"/groups/{group_id}/edit").text).group(1)
    coach_client.post(f"/groups/{group_id}", data={
        "coach_id": ["1", "2"], "why_today": "Visible why", "point_id": [point_id],
        "custom_points": "ZZCUSTOMPOINT", "how_it_went": "ZZHOW"})
    coach_client.post(f"/sessions/{sid}", data={"date": (today_london() + timedelta(days=7)).isoformat(),
                                               "start_time": "18:30", "goal": "Visible goal", "notes": "ZZNOTES"})
    return sid


def test_players_see_only_the_allowed_fields(coach_client, player_client):
    sid = _build(coach_client)
    assert player_client.get(f"/sessions/{sid}").status_code == 404  # not shared yet
    coach_client.post(f"/sessions/{sid}/share")

    html = player_client.get(f"/sessions/{sid}").text
    assert "Visible goal" in html and "Visible activity" in html and "Visible why" in html
    leaked = [m for m in COACH_ONLY if m.lower() in html.lower()]
    assert not leaked, f"coach-only content in the player view: {leaked}"
    assert "/activities/" not in html and "/groups/" not in html and "/edit" not in html

    # The coach's own preview uses the same redacted template (its header still shows the
    # coach's own name and nav, so only the page content is checked).
    preview = coach_client.get(f"/sessions/{sid}?as=player").text
    content = preview[preview.index('<main'):]
    assert not [m for m in COACH_ONLY if m.lower() in content.lower()]


def test_players_cannot_open_past_or_unshared_sessions(coach_client, player_client):
    past = _session(coach_client, days_ahead=-7)
    coach_client.post(f"/sessions/{past}/share")
    assert player_client.get(f"/sessions/{past}").status_code == 404
    assert player_client.get("/sessions/999").status_code == 404
    upcoming = _session(coach_client)
    assert "No session shared yet" in player_client.get("/").text
    coach_client.post(f"/sessions/{upcoming}/share")
    assert f"/sessions/{upcoming}" in player_client.get("/").text
