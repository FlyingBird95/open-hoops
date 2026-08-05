import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from io import BytesIO

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
def teams():
    home = client.post(
        "/api/teams",
        json={"data": {"type": "teams", "attributes": {"name": "Lakers", "is_own": True}}},
    ).json()["data"]["uid"]
    away = client.post(
        "/api/teams",
        json={"data": {"type": "teams", "attributes": {"name": "Celtics", "is_own": False}}},
    ).json()["data"]["uid"]
    return home, away


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_game(mock_task, teams, tmp_path):
    home_uid, away_uid = teams
    mock_task.return_value = None

    resp = client.post(
        "/api/games",
        data={
            "name": "Game 1",
            "date": "2026-01-15",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=[("files", ("game.mp4", BytesIO(b"fake video content"), "video/mp4"))],
    )
    assert resp.status_code == 201
    resource = resp.json()["data"]
    assert resource["attributes"]["name"] == "Game 1"
    assert resource["attributes"]["status"] == "pending"
    mock_task.assert_called_once()


@patch("app.routers.games.post.celery_app.send_task")
def test_list_games(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.return_value = None

    client.post(
        "/api/games",
        data={
            "name": "G1",
            "date": "2026-01-15",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=[("files", ("g.mp4", BytesIO(b"data"), "video/mp4"))],
    )
    resp = client.get("/api/games")
    assert len(resp.json()["data"]) == 1


@patch("app.routers.games.post.celery_app.send_task")
def test_get_game(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.return_value = None

    resp = client.post(
        "/api/games",
        data={
            "name": "G1",
            "date": "2026-01-15",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=[("files", ("g.mp4", BytesIO(b"data"), "video/mp4"))],
    )
    uid = resp.json()["data"]["uid"]
    resp = client.get(f"/api/games/{uid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["name"] == "G1"


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_game_missing_team(mock_task):
    mock_task.return_value = None

    resp = client.post(
        "/api/games",
        data={
            "name": "Game 1",
            "date": "2026-01-15",
            "own_team_uid": "nonexistent",
            "opponent_team_uid": "alsononexistent",
        },
        files=[("files", ("game.mp4", BytesIO(b"fake"), "video/mp4"))],
    )
    assert resp.status_code == 404


def test_get_game_not_found():
    resp = client.get("/api/games/doesnotexist")
    assert resp.status_code == 404
