import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app

TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def team_uid():
    resp = client.post("/api/teams", json={"name": "Lakers", "is_own": True})
    return resp.json()["uid"]


def test_create_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23, "name": "LeBron"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["jersey_number"] == 23
    assert data["team_uid"] == team_uid


def test_list_players_requires_team():
    resp = client.get("/api/players")
    assert resp.status_code == 422


def test_list_players(team_uid):
    client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 3})
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()) == 2


def test_update_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    uid = resp.json()["uid"]
    resp = client.put(f"/api/players/{uid}", json={"name": "LeBron James"})
    assert resp.json()["name"] == "LeBron James"


def test_delete_player(team_uid):
    resp = client.post("/api/players", json={"team_uid": team_uid, "jersey_number": 23})
    uid = resp.json()["uid"]
    resp = client.delete(f"/api/players/{uid}")
    assert resp.status_code == 204
    resp = client.get(f"/api/players?team={team_uid}")
    assert len(resp.json()) == 0
