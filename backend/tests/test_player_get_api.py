import pytest
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.factories import PlayerFactory, TeamFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(db: Session) -> None:
    yield


def test_get_player(db: Session) -> None:
    team = TeamFactory(name="Warriors", is_own=True)
    player = PlayerFactory(team=team, jersey_number=30, name="Curry")

    resp = client.get(f"/api/players/{player.uid}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == "players"
    assert data["uid"] == player.uid
    assert data["attributes"]["jersey_number"] == 30
    assert data["attributes"]["name"] == "Curry"
    assert data["relationships"]["team"]["data"]["uid"] == team.uid


def test_get_player_no_name(db: Session) -> None:
    team = TeamFactory(name="Warriors", is_own=True)
    player = PlayerFactory(team=team, jersey_number=11, name=None)

    resp = client.get(f"/api/players/{player.uid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["name"] is None


def test_get_player_not_found(db: Session) -> None:
    resp = client.get("/api/players/nonexistent")
    assert resp.status_code == 404
