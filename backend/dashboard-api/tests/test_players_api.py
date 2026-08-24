from app.main import app
from fastapi.testclient import TestClient
from open_hoops.service.game.models import Game

client = TestClient(app)


def test_create_player(game: Game):
    team_uid = game.own_team.uid
    resp = client.post(
        "/api/players",
        json={
            "data": {
                "type": "players",
                "attributes": {"jersey_number": 23, "name": "LeBron"},
                "relationships": {"team": {"data": {"type": "teams", "uid": team_uid}}},
            }
        },
    )
    assert resp.status_code == 201
    resource = resp.json()["data"]
    assert resource["attributes"]["jersey_number"] == 23
    assert resource["relationships"]["team"]["data"]["uid"] == team_uid


def test_list_players_requires_team():
    resp = client.get("/api/players")
    assert resp.status_code == 422


def test_list_players(game: Game):
    team_uid = game.own_team.uid
    for num in (23, 3):
        client.post(
            "/api/players",
            json={
                "data": {
                    "type": "players",
                    "attributes": {"jersey_number": num},
                    "relationships": {"team": {"data": {"type": "teams", "uid": team_uid}}},
                }
            },
        )
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()["data"]) == 2


def test_update_player(game: Game):
    team_uid = game.own_team.uid
    resp = client.post(
        "/api/players",
        json={
            "data": {
                "type": "players",
                "attributes": {"jersey_number": 23},
                "relationships": {"team": {"data": {"type": "teams", "uid": team_uid}}},
            }
        },
    )
    uid = resp.json()["data"]["uid"]
    resp = client.patch(
        f"/api/players/{uid}",
        json={"data": {"type": "players", "uid": uid, "attributes": {"name": "LeBron James"}}},
    )
    assert resp.json()["data"]["attributes"]["name"] == "LeBron James"


def test_delete_player(game: Game):
    team_uid = game.own_team.uid
    resp = client.post(
        "/api/players",
        json={
            "data": {
                "type": "players",
                "attributes": {"jersey_number": 23},
                "relationships": {"team": {"data": {"type": "teams", "uid": team_uid}}},
            }
        },
    )
    uid = resp.json()["data"]["uid"]
    resp = client.delete(f"/api/players/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()["data"]) == 0
