from app.models import Team, Player, Video, VideoStatus, generate_uid
from datetime import date


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


def test_video_creation(db):
    home = Team(name="Lakers", is_own=True)
    away = Team(name="Celtics", is_own=False)
    db.add_all([home, away])
    db.commit()
    video = Video(
        name="Game 1",
        date=date(2026, 1, 15),
        file_path="/uploads/game1.mp4",
        home_team_id=home.id,
        away_team_id=away.id,
    )
    db.add(video)
    db.commit()
    db.refresh(video)
    assert video.status == VideoStatus.pending
    assert video.stats_json is None
    assert video.home_team.name == "Lakers"
