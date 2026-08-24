import io
from unittest.mock import patch

from app.main import app
from fastapi.testclient import TestClient
from open_hoops.service.game.models import Game

client = TestClient(app)


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_multiple_files(mock_task, game: Game):
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
            "own_team_uid": game.own_team.uid,
            "opponent_team_uid": game.opponent_team.uid,
        },
        files=files,
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attributes"]["file_count"] == 2
    mock_task.assert_called_once()


@patch("app.routers.games.post.celery_app.send_task")
def test_upload_single_file_via_files_param(mock_task, game: Game):
    mock_task.return_value = None

    response = client.post(
        "/api/games",
        data={
            "name": "Single File Game",
            "date": "2026-08-05",
            "own_team_uid": game.own_team.uid,
            "opponent_team_uid": game.opponent_team.uid,
        },
        files=[("files", ("game.mp4", io.BytesIO(b"fake"), "video/mp4"))],
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["attributes"]["file_count"] == 1
