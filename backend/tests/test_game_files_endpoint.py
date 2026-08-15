import datetime

import pytest
from app.main import app
from fastapi.testclient import TestClient

from open_hoops.db import Base, Game, GameFile, GameStatus, Team, generate_uid
from tests.conftest import TestSession, engine


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


client = TestClient(app)


@pytest.fixture
def game_with_files():
    """Create a game with 2 GameFile rows directly in the DB."""
    db = TestSession()
    try:
        own_team = Team(uid=generate_uid(), name="Own", is_own=True)
        opponent_team = Team(uid=generate_uid(), name="Opponent", is_own=False)
        db.add_all([own_team, opponent_team])
        db.flush()

        game = Game(
            uid=generate_uid(),
            name="Test Game",
            date=datetime.date(2026, 8, 5),
            own_team_id=own_team.id,
            opponent_team_id=opponent_team.id,
            status=GameStatus.pending,
        )
        db.add(game)
        db.flush()

        file0 = GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="/uploads/part0.mp4",
            position=0,
            original_filename="part0.mp4",
            size_bytes=1000,
        )
        file1 = GameFile(
            uid=generate_uid(),
            game_id=game.id,
            file_path="/uploads/part1.mp4",
            position=1,
            original_filename="part1.mp4",
            size_bytes=2000,
        )
        db.add_all([file0, file1])
        db.commit()
        db.refresh(game)
        return game
    finally:
        db.close()


def test_list_game_files(game_with_files):
    """game_with_files fixture creates a game with 2 GameFile rows."""
    response = client.get(f"/api/games/{game_with_files.uid}/files")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 2
    assert data[0]["attributes"]["position"] == 0
    assert data[1]["attributes"]["position"] == 1
    assert data[0]["type"] == "game_files"


def test_list_game_files_attributes(game_with_files):
    """Verify all attributes are present."""
    response = client.get(f"/api/games/{game_with_files.uid}/files")
    assert response.status_code == 200
    body = response.json()
    data = body["data"]
    assert body["meta"]["count"] == 2
    assert data[0]["attributes"]["original_filename"] == "part0.mp4"
    assert data[0]["attributes"]["size_bytes"] == 1000
    assert data[1]["attributes"]["original_filename"] == "part1.mp4"
    assert data[1]["attributes"]["size_bytes"] == 2000


def test_list_game_files_not_found():
    """Returns 404 for unknown game uid."""
    response = client.get("/api/games/nonexistentuid00000000000000000/files")
    assert response.status_code == 404


def test_list_game_files_jsonapi_envelope(game_with_files):
    """Response follows JSON:API 1.1 envelope."""
    response = client.get(f"/api/games/{game_with_files.uid}/files")
    body = response.json()
    assert "data" in body
    assert "meta" in body
    assert "jsonapi" in body
    assert body["jsonapi"]["version"] == "1.1"
