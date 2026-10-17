"""The access boundary: who can reach what. See docs/decisions.md D4, D5."""

import re

from fastapi.routing import APIRoute

from app.auth import safe_next
from app.main import app

PUBLIC = {("GET", "/join/{key}"), ("GET", "/healthz")}
PLAYER_ALLOWED = {("GET", "/"), ("GET", "/sessions/{id}")}


def _routes():
    for route in app.routes:
        if isinstance(route, APIRoute):
            for method in route.methods - {"HEAD"}:
                yield method, route.path


def _call(client, method, path):
    url = re.sub(r"\{[^}]+\}", "1", path)
    return client.request(method, url, data={})


def test_every_route_is_closed_to_outsiders(anon_client):
    for method, path in _routes():
        if (method, path) in PUBLIC:
            continue
        r = _call(anon_client, method, path)
        assert r.status_code == 401, f"{method} {path} gave {r.status_code} to an outsider"


def test_players_only_reach_the_allowlist(player_client):
    for method, path in _routes():
        if (method, path) in PUBLIC | PLAYER_ALLOWED:
            continue
        r = _call(player_client, method, path)
        assert r.status_code in (403, 404), f"{method} {path} gave {r.status_code} to a player"


def test_join_sets_role(anon_client, player_client):
    assert "Ask your coach" in anon_client.get("/").text
    assert anon_client.get("/join/wrong-key").status_code == 404
    assert "No session shared yet" in player_client.get("/").text


def test_join_hides_key_from_referrers(anon_client):
    r = anon_client.get("/join/test-coach-key")
    assert r.status_code == 303
    assert r.headers["referrer-policy"] == "no-referrer"


def test_changing_a_key_logs_out_old_links(coach_client, test_settings, monkeypatch):
    assert coach_client.get("/").status_code == 200
    monkeypatch.setattr(test_settings, "coach_key", "a-brand-new-coach-key")
    assert coach_client.get("/").status_code == 401


def test_player_link_does_not_downgrade_a_coach(coach_client):
    coach_client.get("/join/test-player-key")
    page = coach_client.get("/").text
    assert "Sessions" in page and "John" in page


def test_cross_origin_post_is_rejected(coach_client):
    r = coach_client.post("/who", data={"coach_id": 2}, headers={"Origin": "https://evil.example"})
    assert r.status_code == 403


def test_safe_next():
    assert safe_next("/sessions/3") == "/sessions/3"
    for bad in ("//evil.com", "/\\evil.com", "https://evil.com", "", None):
        assert safe_next(bad) == "/"
