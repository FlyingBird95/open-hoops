from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from open_hoops.service.event.models import GameEvent
from tests.factories import GameEventFactory, GameFactory, GameFileFactory, TeamFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(db: Session) -> None:
    yield


@pytest.fixture
def game_with_event(db: Session) -> dict[str, int | str]:
    home = TeamFactory(name="Heat", is_own=True)
    away = TeamFactory(name="Bucks", is_own=False)
    game = GameFactory(own_team=home, opponent_team=away)
    GameFileFactory(game=game, file_path="uploads/g.mp4", position=0)
    event = GameEventFactory(game=game, type="shot", timestamp_sec=10.0, frame=300)
    return {"game_uid": game.uid, "event_id": event.id}


@patch("app.routers.games.frame.cv2")
def test_get_event_frame(mock_cv2: MagicMock, game_with_event: dict[str, int | str]) -> None:
    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 1000.0
    mock_cap.read.return_value = (True, fake_frame)
    mock_cv2.VideoCapture.return_value = mock_cap
    mock_cv2.CAP_PROP_FRAME_COUNT = 7
    mock_cv2.CAP_PROP_POS_FRAMES = 1
    mock_cv2.imencode.return_value = (True, np.array([0xFF, 0xD8, 0xFF], dtype=np.uint8))
    mock_cv2.IMWRITE_JPEG_QUALITY = 1

    resp = client.get(
        f"/api/games/{game_with_event['game_uid']}/events/{game_with_event['event_id']}/frame"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"


@patch("app.routers.games.frame.cv2")
def test_get_event_frame_with_bbox(
    mock_cv2: MagicMock, game_with_event: dict[str, int | str], db: Session
) -> None:
    event = db.get(GameEvent, game_with_event["event_id"])
    event.bbox_x1 = 100
    event.bbox_y1 = 50
    event.bbox_x2 = 200
    event.bbox_y2 = 150
    db.commit()

    fake_frame = np.zeros((480, 640, 3), dtype=np.uint8)
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = True
    mock_cap.get.return_value = 1000.0
    mock_cap.read.return_value = (True, fake_frame)
    mock_cv2.VideoCapture.return_value = mock_cap
    mock_cv2.CAP_PROP_FRAME_COUNT = 7
    mock_cv2.CAP_PROP_POS_FRAMES = 1
    mock_cv2.imencode.return_value = (True, np.array([0xFF, 0xD8], dtype=np.uint8))
    mock_cv2.IMWRITE_JPEG_QUALITY = 1
    mock_cv2.FONT_HERSHEY_SIMPLEX = 0
    mock_cv2.getTextSize.return_value = ((50, 15), 0)

    resp = client.get(
        f"/api/games/{game_with_event['game_uid']}/events/{game_with_event['event_id']}/frame"
    )
    assert resp.status_code == 200
    mock_cv2.rectangle.assert_called()


def test_get_event_frame_game_not_found(db: Session) -> None:
    resp = client.get("/api/games/nonexistent/events/1/frame")
    assert resp.status_code == 404


def test_get_event_frame_event_not_found(db: Session) -> None:
    home = TeamFactory(name="A", is_own=True)
    away = TeamFactory(name="B", is_own=False)
    game = GameFactory(own_team=home, opponent_team=away)

    resp = client.get(f"/api/games/{game.uid}/events/99999/frame")
    assert resp.status_code == 404


@patch("app.routers.games.frame.cv2")
def test_get_event_frame_video_open_fails(
    mock_cv2: MagicMock, game_with_event: dict[str, int | str]
) -> None:
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_cv2.VideoCapture.return_value = mock_cap

    resp = client.get(
        f"/api/games/{game_with_event['game_uid']}/events/{game_with_event['event_id']}/frame"
    )
    assert resp.status_code == 500
