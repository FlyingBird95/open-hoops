from typing import Any

import pytest
from app.main import app
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from open_hoops.service.team.models import Team
from tests.factories import GameEventFactory, GameFactory, PlayerFactory, TeamFactory

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db(db: Session) -> None:
    yield


@pytest.fixture
def game_data(db: Session) -> dict[str, Any]:
    home = TeamFactory(name="Lakers", is_own=True)
    away = TeamFactory(name="Celtics", is_own=False)
    player = PlayerFactory(team=home, jersey_number=23, name="LeBron")
    game = GameFactory(own_team=home, opponent_team=away)

    return {
        "game_uid": game.uid,
        "home_uid": home.uid,
        "away_uid": away.uid,
        "player_uid": player.uid,
        "game": game,
    }


# --- GET /api/games/{uid}/events ---


def test_list_events_empty(game_data: dict[str, Any]) -> None:
    resp = client.get(f"/api/games/{game_data['game_uid']}/events")
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_list_events(game_data: dict[str, Any], db: Session) -> None:
    game = game_data["game"]
    GameEventFactory(game=game, type="pass", timestamp_sec=5.0, frame=150)
    GameEventFactory(game=game, type="shot", timestamp_sec=10.5, frame=315)

    resp = client.get(f"/api/games/{game_data['game_uid']}/events")
    assert resp.status_code == 200
    assert resp.json()["meta"]["count"] == 2
    events = resp.json()["data"]
    assert events[0]["attributes"]["timestamp_sec"] == 5.0
    assert events[1]["attributes"]["timestamp_sec"] == 10.5


def test_list_events_filter_by_type(game_data: dict[str, Any], db: Session) -> None:
    game = game_data["game"]
    GameEventFactory(game=game, type="shot", timestamp_sec=10.0, frame=300)
    GameEventFactory(game=game, type="pass", timestamp_sec=5.0, frame=150)

    resp = client.get(f"/api/games/{game_data['game_uid']}/events?type=shot")
    assert resp.status_code == 200
    assert resp.json()["meta"]["count"] == 1
    assert resp.json()["data"][0]["attributes"]["type"] == "shot"


def test_list_events_game_not_found(db: Session) -> None:
    resp = client.get("/api/games/nonexistent/events")
    assert resp.status_code == 404


# --- POST /api/games/{uid}/events ---


def test_create_event_minimal(game_data: dict[str, Any]) -> None:
    resp = client.post(
        f"/api/games/{game_data['game_uid']}/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {"type": "rebound", "timestamp_sec": 22.0, "frame": 660},
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["type"] == "game_events"
    assert data["attributes"]["type"] == "rebound"
    assert data["attributes"]["frame"] == 660
    assert data["attributes"]["timestamp_sec"] == 22.0
    assert data["attributes"]["source"] == "manual"


def test_create_event_with_team_and_player(game_data: dict[str, Any]) -> None:
    resp = client.post(
        f"/api/games/{game_data['game_uid']}/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "shot",
                    "timestamp_sec": 15.5,
                    "frame": 465,
                    "team_uid": game_data["home_uid"],
                    "player_uid": game_data["player_uid"],
                },
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["relationships"]["team"]["data"]["uid"] == game_data["home_uid"]
    assert data["relationships"]["player"]["data"]["uid"] == game_data["player_uid"]


def test_create_event_with_player2(game_data: dict[str, Any], db: Session) -> None:
    home = db.query(Team).filter(Team.uid == game_data["home_uid"]).first()
    player2 = PlayerFactory(team=home, jersey_number=3, name="AD")

    resp = client.post(
        f"/api/games/{game_data['game_uid']}/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "pass",
                    "timestamp_sec": 8.0,
                    "frame": 240,
                    "player_uid": game_data["player_uid"],
                    "player2_uid": player2.uid,
                },
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["relationships"]["player"]["data"]["uid"] == game_data["player_uid"]
    assert data["relationships"]["player2"]["data"]["uid"] == player2.uid


@pytest.mark.parametrize(
    ("event_type", "expected_status"),
    [
        ("shot", 200),
        ("pass", 200),
        ("rebound", 200),
        ("dunk", 422),
        ("triple", 422),
    ],
)
def test_create_event_type_validation(
    game_data: dict[str, Any], event_type: str, expected_status: int
) -> None:
    resp = client.post(
        f"/api/games/{game_data['game_uid']}/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {"type": event_type, "timestamp_sec": 1.0, "frame": 30},
            }
        },
    )
    assert resp.status_code == expected_status


def test_create_event_game_not_found(db: Session) -> None:
    resp = client.post(
        "/api/games/nonexistent/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {"type": "shot", "timestamp_sec": 1.0, "frame": 30},
            }
        },
    )
    assert resp.status_code == 404


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("team_uid", "baduid"),
        ("player_uid", "baduid"),
        ("player2_uid", "baduid"),
    ],
)
def test_create_event_invalid_reference(
    game_data: dict[str, Any], field: str, bad_value: str
) -> None:
    resp = client.post(
        f"/api/games/{game_data['game_uid']}/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {"type": "shot", "timestamp_sec": 1.0, "frame": 30, field: bad_value},
            }
        },
    )
    assert resp.status_code == 422


# --- PATCH /api/games/{uid}/events/{event_id} ---


def test_patch_event_type(game_data: dict[str, Any], db: Session) -> None:
    event = GameEventFactory(game=game_data["game"], type="shot", timestamp_sec=10.0, frame=300)

    resp = client.patch(
        f"/api/games/{game_data['game_uid']}/events/{event.id}",
        json={"data": {"type": "game_events", "attributes": {"type": "make"}}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["type"] == "make"


def test_patch_event_assign_team(game_data: dict[str, Any], db: Session) -> None:
    event = GameEventFactory(game=game_data["game"], type="steal", timestamp_sec=20.0, frame=600)

    resp = client.patch(
        f"/api/games/{game_data['game_uid']}/events/{event.id}",
        json={"data": {"type": "game_events", "attributes": {"team_uid": game_data["home_uid"]}}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["relationships"]["team"]["data"]["uid"] == game_data["home_uid"]


def test_patch_event_clear_team(game_data: dict[str, Any], db: Session) -> None:
    home = db.query(Team).filter(Team.uid == game_data["home_uid"]).first()
    event = GameEventFactory(
        game=game_data["game"], type="foul", timestamp_sec=30.0, frame=900, team_id=home.id
    )

    resp = client.patch(
        f"/api/games/{game_data['game_uid']}/events/{event.id}",
        json={"data": {"type": "game_events", "attributes": {"team_uid": None}}},
    )
    assert resp.status_code == 200
    assert "team" not in resp.json()["data"]["relationships"]


def test_patch_event_invalid_type(game_data: dict[str, Any], db: Session) -> None:
    event = GameEventFactory(game=game_data["game"], type="shot", timestamp_sec=10.0, frame=300)

    resp = client.patch(
        f"/api/games/{game_data['game_uid']}/events/{event.id}",
        json={"data": {"type": "game_events", "attributes": {"type": "dunk"}}},
    )
    assert resp.status_code == 422


def test_patch_event_not_found(game_data: dict[str, Any]) -> None:
    resp = client.patch(
        f"/api/games/{game_data['game_uid']}/events/99999",
        json={"data": {"type": "game_events", "attributes": {"type": "shot"}}},
    )
    assert resp.status_code == 404


def test_patch_event_game_not_found(db: Session) -> None:
    resp = client.patch(
        "/api/games/nonexistent/events/1",
        json={"data": {"type": "game_events", "attributes": {"type": "shot"}}},
    )
    assert resp.status_code == 404


# --- DELETE /api/games/{uid}/events/{event_id} ---


def test_delete_event(game_data: dict[str, Any], db: Session) -> None:
    event = GameEventFactory(game=game_data["game"], type="block", timestamp_sec=40.0, frame=1200)

    resp = client.delete(f"/api/games/{game_data['game_uid']}/events/{event.id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/games/{game_data['game_uid']}/events")
    assert resp.json()["meta"]["count"] == 0


def test_delete_event_not_found(game_data: dict[str, Any]) -> None:
    resp = client.delete(f"/api/games/{game_data['game_uid']}/events/99999")
    assert resp.status_code == 404


def test_delete_event_game_not_found(db: Session) -> None:
    resp = client.delete("/api/games/nonexistent/events/1")
    assert resp.status_code == 404
