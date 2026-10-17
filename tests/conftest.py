import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

ORIGIN = {"Origin": "http://testserver"}


@pytest.fixture(autouse=True)
def test_settings(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "coach_key", "test-coach-key")
    monkeypatch.setattr(settings, "player_key", "test-player-key")
    monkeypatch.setattr(settings, "coaches", "John,Dave,Sam")
    monkeypatch.setattr(settings, "https_only", False)
    return settings


def _client():
    return TestClient(app, headers=ORIGIN, follow_redirects=False)


@pytest.fixture
def anon_client():
    with _client() as c:
        yield c


@pytest.fixture
def player_client():
    with _client() as c:
        c.get("/join/test-player-key")
        yield c


@pytest.fixture
def coach_client():
    with _client() as c:
        c.get("/join/test-coach-key")
        c.post("/who", data={"coach_id": 1, "next": "/"})
        yield c
