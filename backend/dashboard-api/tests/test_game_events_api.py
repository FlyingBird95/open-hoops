import pytest
from app.main import app
from fastapi.testclient import TestClient
from open_hoops.service.event.models import GameEvent
from open_hoops.service.game.models import Game
from testhelpers.factories import GameEventFactory, PlayerFactory

client = TestClient(app)


# --- GET /api/events?game={game_uid} ---


def test_list_events_empty(game: Game) -> None:
    resp = client.get("/api/events", params={"game": game.uid})
    assert resp.status_code == 200
    assert resp.json()["data"] == []
    assert resp.json()["meta"]["count"] == 0


def test_list_events(game: Game) -> None:
    GameEventFactory(game=game, type="pass", timestamp_sec=5.0, frame=150)
    GameEventFactory(game=game, type="shot", timestamp_sec=10.5, frame=315)

    resp = client.get("/api/events", params={"game": game.uid})
    assert resp.status_code == 200
    assert resp.json()["meta"]["count"] == 2
    events = resp.json()["data"]
    assert events[0]["attributes"]["timestamp_sec"] == 5.0
    assert events[1]["attributes"]["timestamp_sec"] == 10.5


def test_list_events_filter_by_type(game: Game) -> None:
    GameEventFactory(game=game, type="shot", timestamp_sec=10.0, frame=300)
    GameEventFactory(game=game, type="pass", timestamp_sec=5.0, frame=150)

    resp = client.get("/api/events", params={"game": game.uid, "type": "shot"})
    assert resp.status_code == 200
    assert resp.json()["meta"]["count"] == 1
    assert resp.json()["data"][0]["attributes"]["type"] == "shot"


def test_list_events_game_not_found() -> None:
    resp = client.get("/api/events", params={"game": "nonexistent"})
    assert resp.status_code == 404


# --- GET /api/events/{uid} ---


def test_get_event(game: Game, game_event: GameEvent) -> None:
    resp = client.get(f"/api/events/{game_event.uid}")
    assert resp.status_code == 200
    assert resp.json()["data"]["uid"] == game_event.uid
    assert resp.json()["data"]["attributes"]["type"] == game_event.type


def test_get_event_not_found() -> None:
    resp = client.get("/api/events/nonexistent")
    assert resp.status_code == 404


# --- POST /api/events ---


def test_create_event_minimal(game: Game) -> None:
    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "rebound",
                    "timestamp_sec": 22.0,
                    "frame": 660,
                    "game_uid": game.uid,
                },
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


def test_create_event_with_team_and_player(game: Game) -> None:
    player = PlayerFactory(team=game.own_team, jersey_number=23, name="LeBron")
    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "shot",
                    "timestamp_sec": 15.5,
                    "frame": 465,
                    "game_uid": game.uid,
                    "team_uid": game.own_team.uid,
                    "player_uid": player.uid,
                },
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["relationships"]["team"]["data"]["uid"] == game.own_team.uid
    assert data["relationships"]["player"]["data"]["uid"] == player.uid


def test_create_event_with_player2(game: Game) -> None:
    player1 = PlayerFactory(team=game.own_team, jersey_number=23, name="LeBron")
    player2 = PlayerFactory(team=game.own_team, jersey_number=3, name="AD")

    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "pass",
                    "timestamp_sec": 8.0,
                    "frame": 240,
                    "game_uid": game.uid,
                    "player_uid": player1.uid,
                    "player2_uid": player2.uid,
                },
            }
        },
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["relationships"]["player"]["data"]["uid"] == player1.uid
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
def test_create_event_type_validation(game: Game, event_type: str, expected_status: int) -> None:
    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": event_type,
                    "timestamp_sec": 1.0,
                    "frame": 30,
                    "game_uid": game.uid,
                },
            }
        },
    )
    assert resp.status_code == expected_status


def test_create_event_game_not_found() -> None:
    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "shot",
                    "timestamp_sec": 1.0,
                    "frame": 30,
                    "game_uid": "nonexistent",
                },
            }
        },
    )
    assert resp.status_code == 422


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("team_uid", "baduid"),
        ("player_uid", "baduid"),
        ("player2_uid", "baduid"),
    ],
)
def test_create_event_invalid_reference(game: Game, field: str, bad_value: str) -> None:
    resp = client.post(
        "/api/events",
        json={
            "data": {
                "type": "game_events",
                "attributes": {
                    "type": "shot",
                    "timestamp_sec": 1.0,
                    "frame": 30,
                    "game_uid": game.uid,
                    field: bad_value,
                },
            }
        },
    )
    assert resp.status_code == 422


# --- PATCH /api/events/{uid} ---


def test_patch_event_type(game: Game, game_event: GameEvent) -> None:
    resp = client.patch(
        f"/api/events/{game_event.uid}",
        json={"data": {"type": "game_events", "attributes": {"type": "make"}}},
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["attributes"]["type"] == "make"


def test_patch_event_assign_team(game: Game, game_event: GameEvent) -> None:
    resp = client.patch(
        f"/api/events/{game_event.uid}",
        json={
            "data": {
                "type": "game_events",
                "attributes": {"team_uid": game.own_team.uid},
            }
        },
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["relationships"]["team"]["data"]["uid"] == game.own_team.uid


def test_patch_event_clear_team(game: Game) -> None:
    event = GameEventFactory(
        game=game, type="foul", timestamp_sec=30.0, frame=900, team_id=game.own_team.id
    )

    resp = client.patch(
        f"/api/events/{event.uid}",
        json={"data": {"type": "game_events", "attributes": {"team_uid": None}}},
    )
    assert resp.status_code == 200
    assert "team" not in resp.json()["data"]["relationships"]


def test_patch_event_invalid_type(game: Game, game_event: GameEvent) -> None:
    resp = client.patch(
        f"/api/events/{game_event.uid}",
        json={"data": {"type": "game_events", "attributes": {"type": "dunk"}}},
    )
    assert resp.status_code == 422


def test_patch_event_not_found() -> None:
    resp = client.patch(
        "/api/events/nonexistent",
        json={"data": {"type": "game_events", "attributes": {"type": "shot"}}},
    )
    assert resp.status_code == 404


# --- DELETE /api/events/{uid} ---


def test_delete_event(game: Game, game_event: GameEvent) -> None:
    resp = client.delete(f"/api/events/{game_event.uid}")
    assert resp.status_code == 204

    resp = client.get("/api/events", params={"game": game.uid})
    assert resp.json()["meta"]["count"] == 0


def test_delete_event_not_found() -> None:
    resp = client.delete("/api/events/nonexistent")
    assert resp.status_code == 404
