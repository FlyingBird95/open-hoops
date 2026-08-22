from unittest.mock import MagicMock, patch

import numpy as np
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game, GameFile

client = TestClient(app)


@patch("app.routers.events.frame.cv2")
def test_get_event_frame(
    mock_cv2: MagicMock, game: Game, game_file: GameFile, game_event: GameEvent
) -> None:
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

    resp = client.get(f"/api/events/{game_event.uid}/frame")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"


@patch("app.routers.events.frame.cv2")
def test_get_event_frame_with_bbox(
    mock_cv2: MagicMock, game: Game, game_file: GameFile, game_event: GameEvent, db: Session
) -> None:
    game_event.bbox_x1 = 100
    game_event.bbox_y1 = 50
    game_event.bbox_x2 = 200
    game_event.bbox_y2 = 150
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

    resp = client.get(f"/api/events/{game_event.uid}/frame")
    assert resp.status_code == 200
    mock_cv2.rectangle.assert_called()


def test_get_event_frame_not_found() -> None:
    resp = client.get("/api/events/nonexistent/frame")
    assert resp.status_code == 404


@patch("app.routers.events.frame.cv2")
def test_get_event_frame_video_open_fails(
    mock_cv2: MagicMock, game: Game, game_file: GameFile, game_event: GameEvent
) -> None:
    mock_cap = MagicMock()
    mock_cap.isOpened.return_value = False
    mock_cv2.VideoCapture.return_value = mock_cap

    resp = client.get(f"/api/events/{game_event.uid}/frame")
    assert resp.status_code == 500
