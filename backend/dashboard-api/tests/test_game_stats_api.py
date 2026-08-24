from app.main import app
from fastapi.testclient import TestClient
from open_hoops.service.game.models import Game

from testhelpers.factories import GamePlayerStatsFactory, GameTeamStatsFactory, PlayerFactory

client = TestClient(app)


def test_get_game_stats(game: Game) -> None:
    player = PlayerFactory(team=game.own_team, jersey_number=23, name="LeBron")
    GameTeamStatsFactory(game=game, team=game.own_team, score=105, possession_pct=52.3)
    GameTeamStatsFactory(game=game, team=game.opponent_team, score=98, possession_pct=47.7)
    GamePlayerStatsFactory(
        game=game,
        team=game.own_team,
        player=player,
        jersey_number=23,
        distance_covered_m=3450.5,
        shot_attempts=20,
        shot_makes=10,
        passes_made=8,
        passes_received=12,
        possession_frames=500,
    )

    resp = client.get(f"/api/games/{game.uid}/stats")
    assert resp.status_code == 200

    data = resp.json()["data"]
    assert "team_stats" in data
    assert "player_stats" in data
    assert len(data["team_stats"]) == 2
    assert len(data["player_stats"]) == 1


def test_get_game_stats_team_attributes(game: Game) -> None:
    GameTeamStatsFactory(game=game, team=game.own_team, score=105, possession_pct=52.3)
    GameTeamStatsFactory(game=game, team=game.opponent_team, score=98, possession_pct=47.7)

    resp = client.get(f"/api/games/{game.uid}/stats")
    team_stats = resp.json()["data"]["team_stats"]

    scores = sorted([ts["attributes"]["score"] for ts in team_stats])
    assert scores == [98, 105]

    for ts in team_stats:
        assert "possession_pct" in ts["attributes"]
        assert ts["type"] == "game_team_stats"
        assert "team" in ts["relationships"]
        assert "game" in ts["relationships"]


def test_get_game_stats_player_attributes(game: Game) -> None:
    player = PlayerFactory(team=game.own_team, jersey_number=23, name="LeBron")
    GameTeamStatsFactory(game=game, team=game.own_team, score=105, possession_pct=52.3)
    GameTeamStatsFactory(game=game, team=game.opponent_team, score=98, possession_pct=47.7)
    GamePlayerStatsFactory(
        game=game,
        team=game.own_team,
        player=player,
        jersey_number=23,
        distance_covered_m=3450.5,
        shot_attempts=20,
        shot_makes=10,
        passes_made=8,
        passes_received=12,
        possession_frames=500,
    )

    resp = client.get(f"/api/games/{game.uid}/stats")
    ps = resp.json()["data"]["player_stats"][0]

    assert ps["type"] == "game_player_stats"
    assert ps["attributes"]["jersey_number"] == 23
    assert ps["attributes"]["distance_covered_m"] == 3450.5
    assert ps["attributes"]["shot_attempts"] == 20
    assert ps["attributes"]["shot_makes"] == 10
    assert ps["attributes"]["passes_made"] == 8
    assert ps["attributes"]["passes_received"] == 12
    assert ps["attributes"]["possession_frames"] == 500

    assert ps["relationships"]["player"]["data"]["uid"] == player.uid
    assert ps["relationships"]["team"]["data"]["type"] == "teams"
    assert ps["relationships"]["game"]["data"]["type"] == "games"


def test_get_game_stats_not_found() -> None:
    resp = client.get("/api/games/nonexistent/stats")
    assert resp.status_code == 404


def test_get_game_stats_empty(game: Game) -> None:
    resp = client.get(f"/api/games/{game.uid}/stats")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["team_stats"] == []
    assert data["player_stats"] == []


def test_get_game_stats_player_without_roster_match(game: Game) -> None:
    player = PlayerFactory(team=game.own_team, jersey_number=23, name="LeBron")
    GameTeamStatsFactory(game=game, team=game.own_team, score=105, possession_pct=52.3)
    GameTeamStatsFactory(game=game, team=game.opponent_team, score=98, possession_pct=47.7)
    GamePlayerStatsFactory(
        game=game,
        team=game.own_team,
        player=player,
        jersey_number=23,
        distance_covered_m=3450.5,
        shot_attempts=20,
        shot_makes=10,
        passes_made=8,
        passes_received=12,
        possession_frames=500,
    )
    GamePlayerStatsFactory(
        game=game,
        team=game.own_team,
        player=None,
        player_id=None,
        jersey_number=99,
        distance_covered_m=100.0,
        shot_attempts=2,
        shot_makes=1,
        passes_made=1,
        passes_received=1,
        possession_frames=50,
    )

    resp = client.get(f"/api/games/{game.uid}/stats")
    assert resp.status_code == 200
    player_stats = resp.json()["data"]["player_stats"]
    assert len(player_stats) == 2

    unmatched = next(ps for ps in player_stats if ps["attributes"]["jersey_number"] == 99)
    assert "player" not in unmatched["relationships"]
