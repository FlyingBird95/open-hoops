from datetime import date

from open_hoops.db import Game, GameStatus, Player, Team, generate_uid


def test_generate_uid_length():
    uid = generate_uid()
    assert len(uid) == 32
    assert uid.isalnum()


def test_team_creation(db):
    team = Team(name="Lakers", is_own=True, home_color="#552583", away_color="#fdb927")
    db.add(team)
    db.commit()
    db.refresh(team)
    assert team.id == 1
    assert len(team.uid) == 32
    assert team.is_own is True


def test_player_belongs_to_team(db):
    team = Team(name="Lakers", is_own=True)
    db.add(team)
    db.commit()
    player = Player(team_id=team.id, jersey_number=23, name="LeBron")
    db.add(player)
    db.commit()
    db.refresh(player)
    assert player.team.name == "Lakers"
    assert player.jersey_number == 23


def test_game_creation(db):
    home = Team(name="Lakers", is_own=True)
    away = Team(name="Celtics", is_own=False)
    db.add_all([home, away])
    db.commit()
    game = Game(
        name="Game 1",
        date=date(2026, 1, 15),
        own_team_id=home.id,
        opponent_team_id=away.id,
    )
    db.add(game)
    db.commit()
    db.refresh(game)
    assert game.status == GameStatus.pending
    assert game.duration_seconds == 0.0
    assert game.own_team.name == "Lakers"
