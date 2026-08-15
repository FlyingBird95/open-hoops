import io
from unittest.mock import patch

import pytest
from app.main import app
from fastapi.testclient import TestClient

from open_hoops.db import Base
from tests.conftest import engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def teams():
    """Create home + away teams, return their UIDs."""
    home = client.post(
        "/api/teams",
        json={"data": {"type": "teams", "attributes": {"name": "Home", "is_own": True}}},
    ).json()["data"]["uid"]
    away = client.post(
        "/api/teams",
        json={"data": {"type": "teams", "attributes": {"name": "Away", "is_own": False}}},
    ).json()["data"]["uid"]
    return home, away


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_multiple_files(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.return_value = None

    files = [
        ("files", ("part1.mp4", io.BytesIO(b"fake1"), "video/mp4")),
        ("files", ("part2.mp4", io.BytesIO(b"fake2"), "video/mp4")),
    ]
    response = client.post(
        "/api/games",
        data={
            "name": "Test Game",
            "date": "2026-08-05",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=files,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attributes"]["file_count"] == 2
    mock_task.assert_called_once()


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_single_file_via_files_param(mock_task, teams):
    home_uid, away_uid = teams
    mock_task.return_value = None

    response = client.post(
        "/api/games",
        data={
            "name": "Single File Game",
            "date": "2026-08-05",
            "own_team_uid": home_uid,
            "opponent_team_uid": away_uid,
        },
        files=[("files", ("game.mp4", io.BytesIO(b"fake"), "video/mp4"))],
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attributes"]["file_count"] == 1
