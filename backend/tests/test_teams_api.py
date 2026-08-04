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


def _create_team(**attrs):
    defaults = {"name": "Lakers", "is_own": True, "home_color": "#552583", "away_color": "#FDB927"}
    defaults.update(attrs)
    resp = client.post("/api/teams", json={"data": {"type": "teams", "attributes": defaults}})
    return resp


def test_create_team():
    resp = _create_team()
    assert resp.status_code == 201
    resource = resp.json()["data"]
    assert resource["attributes"]["name"] == "Lakers"
    assert resource["attributes"]["is_own"] is True
    assert len(resource["uid"]) == 32


def test_list_teams_filter():
    _create_team(name="Lakers", is_own=True)
    _create_team(name="Celtics", is_own=False)
    resp = client.get("/api/teams?is_own=true")
    data = resp.json()["data"]
    assert len(data) == 1
    assert data[0]["attributes"]["name"] == "Lakers"


def test_get_team():
    resp = _create_team()
    uid = resp.json()["data"]["uid"]
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["name"] == "Lakers"


def test_update_team():
    resp = _create_team()
    uid = resp.json()["data"]["uid"]
    resp = client.patch(
        f"/api/teams/{uid}",
        json={"data": {"type": "teams", "uid": uid, "attributes": {"name": "LA Lakers"}}},
    )
    assert resp.json()["data"]["attributes"]["name"] == "LA Lakers"


def test_delete_team():
    resp = _create_team()
    uid = resp.json()["data"]["uid"]
    resp = client.delete(f"/api/teams/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 404
