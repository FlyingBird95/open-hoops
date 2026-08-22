import pytest
from app.main import app
from fastapi.testclient import TestClient

from open_hoops.service.player.models import Player

client = TestClient(app)


def test_get_player(player: Player) -> None:
    resp = client.get(f"/api/players/{player.uid}")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == "players"
    assert data["uid"] == player.uid
    assert data["attributes"]["jersey_number"] == player.jersey_number
    assert data["attributes"]["name"] == player.name
    assert data["relationships"]["team"]["data"]["uid"] == player.team.uid


@pytest.mark.parametrize("player__name", [None])
def test_get_player_no_name(player: Player) -> None:
    resp = client.get(f"/api/players/{player.uid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["name"] is None


def test_get_player_not_found() -> None:
    resp = client.get("/api/players/nonexistent")
    assert resp.status_code == 404
