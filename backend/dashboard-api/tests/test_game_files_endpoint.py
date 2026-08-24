from app.main import app
from fastapi.testclient import TestClient
from open_hoops.service.game.models import Game
from testhelpers.factories import GameFileFactory

client = TestClient(app)


def test_list_game_files(game: Game) -> None:
    GameFileFactory(
        game=game,
        file_path="uploads/part0.mp4",
        position=0,
        original_filename="part0.mp4",
        size_bytes=1000,
    )
    GameFileFactory(
        game=game,
        file_path="uploads/part1.mp4",
        position=1,
        original_filename="part1.mp4",
        size_bytes=2000,
    )

    response = client.get(f"/api/games/{game.uid}/files")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["attributes"]["position"] == 0
    assert data[1]["attributes"]["position"] == 1
    assert data[0]["type"] == "game_files"


def test_list_game_files_attributes(game: Game) -> None:
    GameFileFactory(
        game=game,
        file_path="uploads/part0.mp4",
        position=0,
        original_filename="part0.mp4",
        size_bytes=1000,
    )
    GameFileFactory(
        game=game,
        file_path="uploads/part1.mp4",
        position=1,
        original_filename="part1.mp4",
        size_bytes=2000,
    )

    response = client.get(f"/api/games/{game.uid}/files")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert body["meta"]["count"] == 2
    assert data[0]["attributes"]["original_filename"] == "part0.mp4"
    assert data[0]["attributes"]["size_bytes"] == 1000
    assert data[1]["attributes"]["original_filename"] == "part1.mp4"
    assert data[1]["attributes"]["size_bytes"] == 2000


def test_list_game_files_not_found() -> None:
    response = client.get("/api/games/nonexistentuid00000000000000000/files")
    assert response.status_code == 404


def test_list_game_files_jsonapi_envelope(game: Game) -> None:
    GameFileFactory(game=game, file_path="uploads/part0.mp4", position=0)
    GameFileFactory(game=game, file_path="uploads/part1.mp4", position=1)

    response = client.get(f"/api/games/{game.uid}/files")
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert "jsonapi" in body
    assert body["jsonapi"]["version"] == "1.1"
