import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from io import BytesIO

from app.database import Base
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
    home = client.post("/api/teams", json={"name": "Lakers", "is_own": True}).json()
    away = client.post("/api/teams", json={"name": "Celtics", "is_own": False}).json()
    return home["uid"], away["uid"]


@patch("app.routers.videos.analyze_video")
def test_upload_video(mock_task, teams, tmp_path):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    resp = client.post(
        "/api/videos",
        data={
            "name": "Game 1",
            "date": "2026-01-15",
            "home_team_uid": home_uid,
            "away_team_uid": away_uid,
        },
        files={"file": ("game.mp4", BytesIO(b"fake video content"), "video/mp4")},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Game 1"
    assert data["status"] == "pending"
    mock_task.delay.assert_called_once()


@patch("app.routers.videos.analyze_video")
def test_list_videos(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    client.post(
        "/api/videos",
        data={"name": "G1", "date": "2026-01-15", "home_team_uid": home_uid, "away_team_uid": away_uid},
        files={"file": ("g.mp4", BytesIO(b"data"), "video/mp4")},
    )
    resp = client.get("/api/videos")
    assert len(resp.json()) == 1


@patch("app.routers.videos.analyze_video")
def test_get_video(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.delay.return_value = None

    resp = client.post(
        "/api/videos",
        data={"name": "G1", "date": "2026-01-15", "home_team_uid": home_uid, "away_team_uid": away_uid},
        files={"file": ("g.mp4", BytesIO(b"data"), "video/mp4")},
    )
    uid = resp.json()["uid"]
    resp = client.get(f"/api/videos/{uid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "G1"


@patch("app.routers.videos.analyze_video")
def test_upload_video_missing_team(mock_task):
    mock_task.delay.return_value = None

    resp = client.post(
        "/api/videos",
        data={
            "name": "Game 1",
            "date": "2026-01-15",
            "home_team_uid": "nonexistent",
            "away_team_uid": "alsononexistent",
        },
        files={"file": ("game.mp4", BytesIO(b"fake"), "video/mp4")},
    )
    assert resp.status_code == 404


def test_get_video_not_found():
    resp = client.get("/api/videos/doesnotexist")
    assert resp.status_code == 404
