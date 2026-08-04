import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

# Re-use the shared engine/override from conftest.py
from tests.conftest import engine, TestSession


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


def test_create_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True, "home_color": "#552583"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Lakers"
    assert data["is_own"] is True
    assert len(data["uid"]) == 32


def test_list_teams_filter():
    client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    client.post("/api/teams", json={"name": "Celtics", "is_own": False})
    resp = client.get("/api/teams?is_own=true")
    assert len(resp.json()) == 1
    assert resp.json()[0]["name"] == "Lakers"


def test_get_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Lakers"


def test_update_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.put(f"/api/teams/{uid}", json={"name": "LA Lakers"})
    assert resp.json()["name"] == "LA Lakers"


def test_delete_team():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    uid = resp.json()["uid"]
    resp = client.delete(f"/api/teams/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/teams/{uid}")
    assert resp.status_code == 404
