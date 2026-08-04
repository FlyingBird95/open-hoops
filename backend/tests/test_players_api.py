import pytest
from fastapi.testclient import TestClient

from open_hoops.db import Base
from app.main import app

from tests.conftest import engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def team_uid():
    resp = client.post(
        "/api/teams",
        json={"data": {"type": "teams", "attributes": {"name": "Lakers", "is_own": True}}},
    )
    return resp.json()["data"]["uid"]


def test_create_player(team_uid):
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


def test_list_players(team_uid):
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


def test_update_player(team_uid):
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


def test_delete_player(team_uid):
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
